from __future__ import annotations

from typing import NamedTuple

import sqlalchemy as sa
from sqlalchemy import select

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.types import Context

from ckanext.tables.shared import (
    ALL_EXPORTERS,
    ActionHandlerResult,
    BulkActionDefinition,
    ColumnDefinition,
    DatabaseDataSource,
    Row,
    RowActionDefinition,
    TableDefinition,
    formatters,
)

from ckanext.relationship import relation_types
from ckanext.relationship.model.relationship import Relationship
from ckanext.relationship_dashboard.formatters import EntityLinkFormatter


class CanonicalRelationRule(NamedTuple):
    canonical_relation_type: str
    swap_identifiers: bool
    symmetric: bool


def _canonical_relation_rules() -> dict[str, CanonicalRelationRule]:
    rules: dict[str, CanonicalRelationRule] = {}

    for (
        relation_type,
        reverse_relation_type,
    ) in relation_types.get_relation_type_reverse_map().items():
        symmetric = relation_type == reverse_relation_type
        canonical_relation_type = (
            relation_type if symmetric else max(relation_type, reverse_relation_type)
        )
        rules[relation_type] = CanonicalRelationRule(
            canonical_relation_type=canonical_relation_type,
            swap_identifiers=(
                not symmetric and relation_type != canonical_relation_type
            ),
            symmetric=symmetric,
        )

    return rules


def _canonical_subject_id(
    rules: dict[str, CanonicalRelationRule],
) -> sa.Label[str]:
    ordered_subject = sa.case(
        (
            Relationship.subject_id <= Relationship.object_id,
            Relationship.subject_id,
        ),
        else_=Relationship.object_id,
    )

    whens = []
    for relation_type, rule in rules.items():
        if rule.symmetric:
            whens.append((Relationship.relation_type == relation_type, ordered_subject))
        elif rule.swap_identifiers:
            whens.append(
                (Relationship.relation_type == relation_type, Relationship.object_id)
            )

    return sa.case(*whens, else_=Relationship.subject_id).label("subject_id")


def _canonical_object_id(
    rules: dict[str, CanonicalRelationRule],
) -> sa.Label[str]:
    ordered_object = sa.case(
        (
            Relationship.subject_id <= Relationship.object_id,
            Relationship.object_id,
        ),
        else_=Relationship.subject_id,
    )

    whens = []
    for relation_type, rule in rules.items():
        if rule.symmetric:
            whens.append((Relationship.relation_type == relation_type, ordered_object))
        elif rule.swap_identifiers:
            whens.append(
                (Relationship.relation_type == relation_type, Relationship.subject_id)
            )

    return sa.case(*whens, else_=Relationship.object_id).label("object_id")


def _canonical_relation_type(
    rules: dict[str, CanonicalRelationRule],
) -> sa.Label[str]:
    whens = []
    for relation_type, rule in rules.items():
        if rule.canonical_relation_type == relation_type:
            continue

        whens.append(
            (
                Relationship.relation_type == relation_type,
                sa.literal(rule.canonical_relation_type),
            )
        )

    return sa.case(*whens, else_=Relationship.relation_type).label("relation_type")


def _canonical_relationships() -> sa.Subquery:
    rules = _canonical_relation_rules()
    subject_id = _canonical_subject_id(rules)
    object_id = _canonical_object_id(rules)
    relation_type = _canonical_relation_type(rules)

    return (
        select(
            sa.func.min(Relationship.id).label("id"),
            subject_id,
            object_id,
            relation_type,
            sa.func.min(Relationship.created_at).label("created_at"),
            sa.func.nullif(
                sa.func.max(sa.cast(Relationship.extras, sa.Text)),
                "{}",
            ).label("extras"),
        )
        .group_by(subject_id, object_id, relation_type)
        .subquery("canonical_relationships")
    )


def _package_entities() -> sa.Subquery:
    return (
        select(
            model.Package.id.label("entity_id"),
            model.Package.name.label("entity_name"),
            sa.func.coalesce(model.Package.title, model.Package.name).label(
                "entity_label"
            ),
            sa.literal("package").label("entity_kind"),
        )
        .where(model.Package.state != "deleted")
        .subquery("package_entities")
    )


def _group_entities() -> sa.Subquery:
    return (
        select(
            model.Group.id.label("entity_id"),
            model.Group.name.label("entity_name"),
            sa.func.coalesce(model.Group.title, model.Group.name).label("entity_label"),
            sa.case(
                (model.Group.is_organization.is_(True), sa.literal("organization")),
                else_=sa.literal("group"),
            ).label("entity_kind"),
        )
        .where(model.Group.state != "deleted")
        .subquery("group_entities")
    )


def _entity_match(entity_alias: sa.Subquery, entity_ref: sa.ColumnElement[str]):
    return sa.or_(
        entity_alias.c.entity_id == entity_ref,
        entity_alias.c.entity_name == entity_ref,
    )


class RelationshipDashboardTable(TableDefinition):
    def __init__(self):
        canonical_relationships = _canonical_relationships()
        package_entities = _package_entities()
        group_entities = _group_entities()
        subject_package = package_entities.alias("subject_package")
        subject_group = group_entities.alias("subject_group")
        object_package = package_entities.alias("object_package")
        object_group = group_entities.alias("object_group")

        subject_label = sa.func.coalesce(
            subject_package.c.entity_label,
            subject_group.c.entity_label,
            canonical_relationships.c.subject_id,
        ).label("subject_label")
        object_label = sa.func.coalesce(
            object_package.c.entity_label,
            object_group.c.entity_label,
            canonical_relationships.c.object_id,
        ).label("object_label")
        subject_kind = sa.func.coalesce(
            subject_package.c.entity_kind,
            subject_group.c.entity_kind,
            sa.literal("unknown"),
        ).label("subject_kind")
        object_kind = sa.func.coalesce(
            object_package.c.entity_kind,
            object_group.c.entity_kind,
            sa.literal("unknown"),
        ).label("object_kind")

        super().__init__(
            name="relationship",
            data_source=DatabaseDataSource(
                stmt=select(
                    canonical_relationships.c.id,
                    canonical_relationships.c.subject_id,
                    subject_label,
                    subject_kind,
                    canonical_relationships.c.object_id,
                    object_label,
                    object_kind,
                    canonical_relationships.c.relation_type,
                    canonical_relationships.c.created_at,
                    canonical_relationships.c.extras,
                )
                .select_from(canonical_relationships)
                .outerjoin(
                    subject_package,
                    _entity_match(
                        subject_package, canonical_relationships.c.subject_id
                    ),
                )
                .outerjoin(
                    subject_group,
                    _entity_match(subject_group, canonical_relationships.c.subject_id),
                )
                .outerjoin(
                    object_package,
                    _entity_match(object_package, canonical_relationships.c.object_id),
                )
                .outerjoin(
                    object_group,
                    _entity_match(object_group, canonical_relationships.c.object_id),
                )
                .order_by(canonical_relationships.c.created_at.desc()),
            ),
            columns=[
                ColumnDefinition(
                    field="subject_label",
                    title=tk._("Subject"),
                    width=240,
                    tabulator_formatter="html",
                    formatters=[
                        (
                            EntityLinkFormatter,
                            {
                                "entity_id_field": "subject_id",
                                "entity_kind_field": "subject_kind",
                            },
                        )
                    ],
                ),
                ColumnDefinition(
                    field="subject_kind",
                    title=tk._("Subject type"),
                    width=140,
                ),
                ColumnDefinition(
                    field="object_label",
                    title=tk._("Object"),
                    width=240,
                    tabulator_formatter="html",
                    formatters=[
                        (
                            EntityLinkFormatter,
                            {
                                "entity_id_field": "object_id",
                                "entity_kind_field": "object_kind",
                            },
                        )
                    ],
                ),
                ColumnDefinition(
                    field="object_kind",
                    title=tk._("Object type"),
                    width=140,
                ),
                ColumnDefinition(
                    field="relation_type",
                    title=tk._("Relationship type"),
                    width=160,
                ),
                ColumnDefinition(
                    field="created_at",
                    title=tk._("Created"),
                    formatters=[
                        (
                            formatters.DateFormatter,
                            {"date_format": "%Y-%m-%d %H:%M:%S"},
                        ),
                    ],
                    tabulator_formatter="html",
                    resizable=False,
                    width=180,
                ),
                ColumnDefinition(
                    field="extras",
                    title=tk._("Extras"),
                    formatters=[
                        (formatters.NoneAsEmptyFormatter, {}),
                        (
                            formatters.DialogModalFormatter,
                            {
                                "max_length": 60,
                                "modal_title": tk._("Relationship extras"),
                            },
                        ),
                    ],
                    tabulator_formatter="html",
                    width=200,
                ),
            ],
            row_actions=[
                RowActionDefinition(
                    action="delete",
                    label=tk._("Delete"),
                    icon="fa fa-trash",
                    callback=self.row_action_delete,
                    with_confirmation=True,
                ),
            ],
            bulk_actions=[
                BulkActionDefinition(
                    action="delete",
                    label=tk._("Delete selected relationships"),
                    icon="fa fa-trash",
                    callback=self.bulk_action_delete,
                )
            ],
            exporters=ALL_EXPORTERS,
            page_size=25,
            placeholder=tk._("No relationships found"),
        )

    @staticmethod
    def _delete_relation(row: Row) -> None:
        tk.get_action("relationship_relation_delete")(
            {"ignore_auth": True},
            {
                "subject_id": row["subject_id"],
                "object_id": row["object_id"],
                "relation_type": row["relation_type"],
            },
        )

    @classmethod
    def row_action_delete(cls, row: Row) -> ActionHandlerResult:
        cls._delete_relation(row)
        return ActionHandlerResult(success=True, error=None)

    @classmethod
    def bulk_action_delete(cls, rows: list[Row]) -> ActionHandlerResult:
        for row in rows:
            cls._delete_relation(row)

        return ActionHandlerResult(success=True, error=None)

    @classmethod
    def check_access(cls, context: Context) -> None:
        tk.check_access("sysadmin", context)
