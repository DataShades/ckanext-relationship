from __future__ import annotations

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

from ckanext.relationship.model.relationship import Relationship
from ckanext.relationship_dashboard.formatters import EntityLinkFormatter


def _canonical_subject_id() -> sa.Label[str]:
    ordered_subject = sa.case(
        (
            Relationship.subject_id <= Relationship.object_id,
            Relationship.subject_id,
        ),
        else_=Relationship.object_id,
    )

    return sa.case(
        (Relationship.relation_type == "child_of", Relationship.object_id),
        (Relationship.relation_type == "related_to", ordered_subject),
        else_=Relationship.subject_id,
    ).label("subject_id")


def _canonical_object_id() -> sa.Label[str]:
    ordered_object = sa.case(
        (
            Relationship.subject_id <= Relationship.object_id,
            Relationship.object_id,
        ),
        else_=Relationship.subject_id,
    )

    return sa.case(
        (Relationship.relation_type == "child_of", Relationship.subject_id),
        (Relationship.relation_type == "related_to", ordered_object),
        else_=Relationship.object_id,
    ).label("object_id")


def _canonical_relation_type() -> sa.Label[str]:
    return sa.case(
        (Relationship.relation_type == "child_of", sa.literal("parent_of")),
        else_=Relationship.relation_type,
    ).label("relation_type")


def _entity_label(entity_ref: sa.Label[str]) -> sa.Label[str]:
    package_label = (
        select(sa.func.coalesce(model.Package.title, model.Package.name))
        .where(
            model.Package.state != "deleted",
            sa.or_(
                model.Package.id == entity_ref,
                model.Package.name == entity_ref,
            ),
        )
        .limit(1)
        .scalar_subquery()
    )
    group_label = (
        select(sa.func.coalesce(model.Group.title, model.Group.name))
        .where(
            model.Group.state != "deleted",
            sa.or_(
                model.Group.id == entity_ref,
                model.Group.name == entity_ref,
            ),
        )
        .limit(1)
        .scalar_subquery()
    )

    return sa.func.coalesce(package_label, group_label, entity_ref).label(
        entity_ref.name.replace("_id", "_label")
    )


def _entity_kind(entity_ref: sa.Label[str]) -> sa.Label[str]:
    package_kind = (
        select(sa.literal("package"))
        .where(
            model.Package.state != "deleted",
            sa.or_(
                model.Package.id == entity_ref,
                model.Package.name == entity_ref,
            ),
        )
        .limit(1)
        .scalar_subquery()
    )
    group_kind = (
        select(
            sa.case(
                (model.Group.is_organization.is_(True), sa.literal("organization")),
                else_=sa.literal("group"),
            )
        )
        .where(
            model.Group.state != "deleted",
            sa.or_(
                model.Group.id == entity_ref,
                model.Group.name == entity_ref,
            ),
        )
        .limit(1)
        .scalar_subquery()
    )

    return sa.func.coalesce(package_kind, group_kind, sa.literal("unknown")).label(
        entity_ref.name.replace("_id", "_kind")
    )


class RelationshipDashboardTable(TableDefinition):
    def __init__(self):
        subject_id = _canonical_subject_id()
        object_id = _canonical_object_id()
        relation_type = _canonical_relation_type()
        subject_label = _entity_label(subject_id)
        object_label = _entity_label(object_id)
        subject_kind = _entity_kind(subject_id)
        object_kind = _entity_kind(object_id)
        created_at = sa.func.min(Relationship.created_at).label("created_at")
        extras = sa.func.nullif(
            sa.func.max(sa.cast(Relationship.extras, sa.Text)),
            "{}",
        ).label("extras")

        super().__init__(
            name="relationship",
            data_source=DatabaseDataSource(
                stmt=select(
                    sa.func.min(Relationship.id).label("id"),
                    subject_id,
                    subject_label,
                    subject_kind,
                    object_id,
                    object_label,
                    object_kind,
                    relation_type,
                    created_at,
                    extras,
                )
                .group_by(subject_id, subject_label, subject_kind)
                .group_by(object_id, object_label, object_kind)
                .group_by(relation_type)
                .order_by(created_at.desc()),
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
