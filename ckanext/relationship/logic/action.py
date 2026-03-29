from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from flask import jsonify
from flask.wrappers import Response

import ckan.plugins.toolkit as tk
from ckan import authz, logic
from ckan.lib.search.query import solr_literal
from ckan.logic import validate
from ckan.types import Action, Context

from ckanext.relationship import relation_types, utils
from ckanext.relationship.config import (
    allow_name_based_relation_create,
    views_without_relationships_in_package_show,
)
from ckanext.relationship.logic import schema
from ckanext.relationship.model.relationship import Relationship
from ckanext.relationship.utils import entity_name_by_id


def get_actions():
    return {
        "relationship_relation_create": relationship_relation_create,
        "relationship_relation_delete": relationship_relation_delete,
        "relationship_relations_list": relationship_relations_list,
        "relationship_relations_ids_list": relationship_relations_ids_list,
        "relationship_get_entity_list": relationship_get_entity_list,
        "relationship_autocomplete": relationship_autocomplete,
        "package_show": package_show,
    }


@validate(schema.relation_create)
def relationship_relation_create(
    context: Context, data_dict: dict[str, Any]
) -> list[dict[str, Any]]:
    """Create relation with specified type (relation_type) between two entities
    specified by ids (subject_id, object_id). Also create reverse relation.
    """
    tk.check_access("relationship_relation_create", context, data_dict)

    subject_id = data_dict["subject_id"]
    object_id = data_dict["object_id"]
    relation_type = data_dict["relation_type"]
    extras = data_dict.get("extras", {})

    _validate_relation_identifiers(subject_id, object_id)

    if Relationship.by_object_id(subject_id, object_id, relation_type):
        return []

    relation = Relationship(
        subject_id=subject_id,
        object_id=object_id,
        relation_type=relation_type,
        extras=extras,
    )

    reverse_relation = Relationship(
        subject_id=object_id,
        object_id=subject_id,
        relation_type=relation_types.get_reverse_relation_type(relation_type),
        extras=extras,
    )

    context["session"].add(relation)
    context["session"].add(reverse_relation)
    context["session"].commit()

    return [rel.as_dict() for rel in (relation, reverse_relation)]


def _validate_relation_identifiers(subject_id: str, object_id: str) -> None:
    subject_uses_id = utils.is_uuid(subject_id)
    object_uses_id = utils.is_uuid(object_id)

    if subject_uses_id != object_uses_id:
        message = tk._("subject_id and object_id must both use ids or both use names")
        raise tk.ValidationError(
            {
                "subject_id": [message],
                "object_id": [message],
            }
        )

    if not subject_uses_id and not allow_name_based_relation_create():
        raise tk.ValidationError(
            {
                "object_id": [
                    tk._(
                        "Creating relationships by name is disabled by "
                        "ckanext.relationship.allow_name_based_relation_create"
                    )
                ]
            }
        )


@validate(schema.relation_delete)
def relationship_relation_delete(
    context: Context, data_dict: dict[str, Any]
) -> list[dict[str, str]]:
    """Delete relation with specified type (relation_type) between two entities
    specified by ids (subject_id, object_id). Also delete reverse relation.
    """
    tk.check_access("relationship_relation_delete", context, data_dict)

    subject_id = data_dict["subject_id"]
    subject_name = entity_name_by_id(data_dict["subject_id"])
    object_id = data_dict["object_id"]
    object_name = entity_name_by_id(data_dict["object_id"])
    relation_type = data_dict.get("relation_type")

    relation = (
        context["session"]
        .query(Relationship)
        .filter(
            sa.or_(
                Relationship.subject_id == subject_id,
                Relationship.subject_id == subject_name,
            ),
            sa.or_(
                Relationship.object_id == object_id,
                Relationship.object_id == object_name,
            ),
        )
    )

    if relation_type:
        relation = relation.filter(Relationship.relation_type == relation_type)

    relation = relation.all()

    reverse_relation = (
        context["session"]
        .query(Relationship)
        .filter(
            sa.or_(
                Relationship.subject_id == object_id,
                Relationship.subject_id == object_name,
            ),
            sa.or_(
                Relationship.object_id == subject_id,
                Relationship.object_id == subject_name,
            ),
        )
    )

    if relation_type:
        reverse_relation = reverse_relation.filter(
            Relationship.relation_type
            == relation_types.get_reverse_relation_type(relation_type),
        )

    reverse_relation = reverse_relation.all()

    [context["session"].delete(rel) for rel in relation]
    [context["session"].delete(rel) for rel in reverse_relation]
    context["session"].commit()
    return [rel[0].as_dict() for rel in (relation, reverse_relation) if len(rel) > 0]


@validate(schema.relations_list)
def relationship_relations_list(
    context: Context, data_dict: dict[str, Any]
) -> list[dict[str, str]]:
    """Return a list of dictionaries representing the relations of a specified entity
    (object_entity, object_type) related to the specified type of relation
    (relation_type) with an entity specified by its id (subject_id).
    """
    tk.check_access("relationship_relations_list", context, data_dict)

    subject_id = data_dict["subject_id"]
    object_entity = data_dict.get("object_entity")
    object_entity = (
        "group" if object_entity and object_entity == "organization" else object_entity
    )
    object_type = data_dict.get("object_type")
    relation_type = data_dict.get("relation_type")

    relations = Relationship.by_subject_id(
        subject_id,
        object_entity,
        object_type,
        relation_type,
    )
    if not relations:
        return []
    return [rel.as_dict() for rel in relations]


@validate(schema.relations_ids_list)
def relationship_relations_ids_list(
    context: Context, data_dict: dict[str, Any]
) -> list[str]:
    """Return ids list of specified entity (object_entity, object_type) related
    with specified type of relation (relation_type) with entity specified
    by id (subject_id).
    """
    tk.check_access("relationship_relations_ids_list", context, data_dict)

    rel_list = relationship_relations_list(context, data_dict)

    return list({rel["object_id"] for rel in rel_list})


@validate(schema.get_entity_list)
def relationship_get_entity_list(
    context: Context, data_dict: dict[str, Any]
) -> list[str]:
    """Return ids list of specified entity (entity, entity_type)."""
    tk.check_access("relationship_get_entity_list", context, data_dict)

    entity = data_dict["entity"]
    entity = entity if entity != "organization" else "group"
    entity_class = logic.model_name_to_class(context["model"], entity)

    return (
        context["session"]
        .query(entity_class.id, entity_class.name, entity_class.title)
        .filter(entity_class.state != "deleted")
        .filter(entity_class.type == data_dict["entity_type"])
        .all()
    )


@validate(schema.autocomplete)
def relationship_autocomplete(context: Context, data_dict: dict[str, Any]) -> Response:
    fq = f"type:{data_dict['entity_type']} -id:{data_dict['current_entity_id']}"
    query = data_dict.get("incomplete", "")

    if data_dict.get("owned_only") and not (
        authz.is_sysadmin(tk.current_user.id) and not data_dict.get("check_sysadmin")
    ):
        fq += f" creator_user_id:{tk.current_user.id}"

    if query:
        query = " OR ".join(
            [
                "name_ngram:{0}",
                "title_ngram:{0}",
                "name:{0}",
                "title:{0}",
            ]
        ).format(solr_literal(query))

    packages = tk.get_action("package_search")(
        {},
        {
            "q": query,
            "fq": fq,
            "fl": "id, title",
            "rows": 100,
            "include_private": True,
            "sort": "score desc",
        },
    )["results"]

    if data_dict.get("updatable_only"):
        packages = [
            pkg
            for pkg in packages
            if tk.h.check_access("package_update", {"id": pkg["id"]})
        ]

    helper_name = (
        data_dict.get("format_autocomplete_helper")
        or "relationship_format_autocomplete"
    )
    format_autocomplete_helper: Any = getattr(
        tk.h,
        helper_name,
        tk.h.relationship_format_autocomplete,
    )

    return jsonify(format_autocomplete_helper(packages))


@tk.chained_action
@tk.side_effect_free
def package_show(
    next_: Action, context: Context, data_dict: dict[str, Any]
) -> dict[str, Any]:
    result = next_(context, data_dict)

    pkg_id = result["id"]
    pkg_type = result["type"]

    views_without_relationships = views_without_relationships_in_package_show()

    if (
        tk.get_endpoint()[1] in views_without_relationships
        and "with_relationships" not in data_dict
    ):
        relations_info = utils.get_relations_info(pkg_type)
        for (
            related_entity,
            related_entity_type,
            relation_type,
        ) in relations_info:
            field = utils.get_relation_field(
                pkg_type,
                related_entity,
                related_entity_type,
                relation_type,
            )
            result.pop(field["field_name"], None)
        return result

    relations_info = utils.get_relations_info(pkg_type)
    for (
        related_entity,
        related_entity_type,
        relation_type,
    ) in relations_info:
        field = utils.get_relation_field(
            pkg_type,
            related_entity,
            related_entity_type,
            relation_type,
        )
        result[field["field_name"]] = [
            relation["object_id"]
            for relation in tk.get_action("relationship_relations_list")(
                context,
                {
                    "subject_id": pkg_id,
                    "object_entity": related_entity,
                    "object_type": related_entity_type,
                    "relation_type": relation_type,
                },
            )
        ]
    return result
