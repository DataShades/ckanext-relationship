from __future__ import annotations

import contextlib
from typing import Any, cast

import ckan.plugins.toolkit as tk
from ckan import plugins as p
from ckan.common import CKANConfig
from ckan.lib.search import rebuild
from ckan.logic import NotFound
from ckan.types import Context

import ckanext.scheming.helpers as sch

from ckanext.relationship import config, helpers, relation_types, utils, views
from ckanext.relationship.logic import action, auth, validators
from ckanext.relationship.model.relationship import Relationship


class RelationshipPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IValidators)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IBlueprint)
    p.implements(p.IPackageController, inherit=True)

    # IConfigurer
    def update_config(self, config_: CKANConfig):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "relationship")

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()

    # IValidators
    def get_validators(self):
        return validators.get_validators()

    # ITemplateHelpers
    def get_helpers(self):
        return helpers.get_helpers()

    # IBlueprint
    def get_blueprint(self):
        return views.get_blueprints()

    # IPackageController
    def after_dataset_create(self, context: Context, pkg_dict: dict[str, Any]):
        context = context.copy()
        context.pop("__auth_audit", None)
        return _update_relations(context, pkg_dict)

    def after_dataset_update(self, context: Context, pkg_dict: dict[str, Any]):
        context = context.copy()
        context.pop("__auth_audit", None)
        return _update_relations(context, pkg_dict)

    def after_dataset_delete(self, context: Context, pkg_dict: dict[str, Any]):
        context = context.copy()
        context.pop("__auth_audit", None)

        subject_id = pkg_dict["id"]

        relations_ids_list = tk.get_action("relationship_relations_ids_list")(
            context,
            {"subject_id": subject_id},
        )

        for object_id in relations_ids_list:
            tk.get_action("relationship_relation_delete")(
                context,
                {"subject_id": subject_id, "object_id": object_id},
            )

            with contextlib.suppress(NotFound):
                _rebuild_package_index(object_id)
        _rebuild_package_index(subject_id)

    def before_dataset_index(self, pkg_dict: dict[str, Any]):
        pkg_id = pkg_dict["id"]
        pkg_type = pkg_dict["type"]
        schema = cast(
            "dict[str, Any] | None", sch.scheming_get_schema("dataset", pkg_type)
        )
        if not schema:
            return pkg_dict
        relations_info = utils.get_relations_info(pkg_type)
        for (
            related_entity,
            related_entity_type,
            relation_type,
        ) in relations_info:
            relations_ids = tk.get_action("relationship_relations_ids_list")(
                {},
                {
                    "subject_id": pkg_id,
                    "object_entity": related_entity,
                    "object_type": related_entity_type,
                    "relation_type": relation_type,
                },
            )

            if not relations_ids:
                continue
            field = utils.get_relation_field(
                pkg_type,
                related_entity,
                related_entity_type,
                relation_type,
            )
            pkg_dict[f"vocab_{field['field_name']}"] = relations_ids

            pkg_dict.pop(field["field_name"], None)

        return pkg_dict

    # CKAN < 2.10 hooks
    def after_create(self, context: Context, data_dict: dict[str, Any]):
        return self.after_dataset_create(context, data_dict)

    def after_update(self, context: Context, data_dict: dict[str, Any]):
        return self.after_dataset_update(context, data_dict)

    def after_delete(self, context: Context, data_dict: dict[str, Any]):
        return self.after_dataset_delete(context, data_dict)

    def before_index(self, pkg_dict: dict[str, Any]):
        return self.before_dataset_index(pkg_dict)


if tk.check_ckan_version("2.10"):
    tk.blanket.config_declarations(RelationshipPlugin)


def _update_relations(context: Context, pkg_dict: dict[str, Any]):
    subject_id = pkg_dict["id"]
    subject_name = pkg_dict["name"]
    add_relations = pkg_dict.get("add_relations", [])
    del_relations = pkg_dict.get("del_relations", [])
    rebuilt_package_ids = _canonicalize_existing_relations(context, pkg_dict)

    if not add_relations and not del_relations:
        _rebuild_related_package_indexes(rebuilt_package_ids)
        return pkg_dict

    for object_id, relation_type in del_relations + add_relations:
        if (object_id, relation_type) in add_relations:
            relation_subject_id = (
                subject_id if utils.is_uuid(object_id) else subject_name
            )
            if (
                not utils.is_uuid(object_id)
                and not config.allow_name_based_relation_create()
            ):
                raise tk.ValidationError(
                    {
                        "__after": [
                            tk._(
                                "Creating relationships by name is disabled by "
                                "ckanext.relationship.allow_name_based_relation_create"
                            )
                        ]
                    }
                )
            tk.get_action("relationship_relation_create")(
                context,
                {
                    "subject_id": relation_subject_id,
                    "object_id": object_id,
                    "relation_type": relation_type,
                },
            )
            if utils.is_uuid(object_id):
                rebuilt_package_ids.add(object_id)
        else:
            tk.get_action("relationship_relation_delete")(
                context,
                {
                    "subject_id": subject_id,
                    "object_id": object_id,
                    "relation_type": relation_type,
                },
            )
            if utils.is_uuid(object_id):
                rebuilt_package_ids.add(object_id)

    _rebuild_related_package_indexes(rebuilt_package_ids | {subject_id})
    return pkg_dict


def _rebuild_package_index(package_id: str) -> None:
    if config.async_package_index_rebuild():
        tk.enqueue_job(rebuild, [package_id], queue=config.redis_queue_name())
    else:
        rebuild(package_id)


def _canonicalize_existing_relations(
    context: Context, pkg_dict: dict[str, Any]
) -> set[str]:
    subject_id = pkg_dict["id"]
    pkg_type = pkg_dict["type"]
    relations_info = utils.get_relations_info(pkg_type)
    repaired_package_ids: set[str] = set()
    repair_jobs: set[tuple[str, str, str, str, str]] = set()

    for related_entity, related_entity_type, relation_type in relations_info:
        current_relations = tk.get_action("relationship_relations_list")(
            context,
            {
                "subject_id": subject_id,
                "object_entity": related_entity,
                "object_type": related_entity_type,
                "relation_type": relation_type,
            },
        )
        for relation in current_relations:
            canonical_object_id = (
                utils.resolve_entity_name_to_id(
                    related_entity,
                    related_entity_type,
                    relation["object_id"],
                )
                or relation["object_id"]
            )

            if not utils.is_uuid(canonical_object_id):
                continue

            if (
                relation["subject_id"] == subject_id
                and relation["object_id"] == canonical_object_id
            ):
                continue

            repair_jobs.add(
                (
                    relation["subject_id"],
                    relation["object_id"],
                    relation["relation_type"],
                    subject_id,
                    canonical_object_id,
                )
            )

    if not repair_jobs:
        return repaired_package_ids

    for (
        current_subject_id,
        current_object_id,
        relation_type,
        canonical_subject_id,
        canonical_object_id,
    ) in repair_jobs:
        if _canonicalize_relation_pair(
            context["session"],
            (current_subject_id, current_object_id, relation_type),
            (canonical_subject_id, canonical_object_id),
        ):
            repaired_package_ids.add(canonical_subject_id)
            repaired_package_ids.add(canonical_object_id)

    if repaired_package_ids:
        context["session"].commit()

    return repaired_package_ids


def _canonicalize_relation_pair(
    session: Any,
    current_relation: tuple[str, str, str],
    canonical_relation: tuple[str, str],
) -> bool:
    current_subject_id, current_object_id, relation_type = current_relation
    canonical_subject_id, canonical_object_id = canonical_relation
    reverse_relation_type = relation_types.get_reverse_relation_type(relation_type)
    current_forward = _exact_relation(
        session,
        current_subject_id,
        current_object_id,
        relation_type,
    )
    current_reverse = _exact_relation(
        session,
        current_object_id,
        current_subject_id,
        reverse_relation_type,
    )
    target_forward = _exact_relation(
        session,
        canonical_subject_id,
        canonical_object_id,
        relation_type,
    )
    target_reverse = _exact_relation(
        session,
        canonical_object_id,
        canonical_subject_id,
        reverse_relation_type,
    )

    changed = False

    if current_forward is not None:
        if target_forward is None:
            current_forward.subject_id = canonical_subject_id
            current_forward.object_id = canonical_object_id
            changed = True
        elif current_forward is not target_forward:
            session.delete(current_forward)
            changed = True

    if current_reverse is not None:
        if target_reverse is None:
            current_reverse.subject_id = canonical_object_id
            current_reverse.object_id = canonical_subject_id
            changed = True
        elif current_reverse is not target_reverse:
            session.delete(current_reverse)
            changed = True

    return changed


def _exact_relation(
    session: Any, subject_id: str, object_id: str, relation_type: str
) -> Any:
    return (
        session.query(Relationship)
        .filter_by(
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )
        .one_or_none()
    )


def _rebuild_related_package_indexes(package_ids: set[str]) -> None:
    for package_id in package_ids:
        with contextlib.suppress(NotFound):
            _rebuild_package_index(package_id)
