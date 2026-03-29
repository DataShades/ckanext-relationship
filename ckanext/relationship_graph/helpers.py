from __future__ import annotations

import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.relationship import config, relation_types, utils
from ckanext.relationship.model.relationship import Relationship


def get_helpers():
    helper_functions = [
        relationship_has_relations,
        relationship_has_existing_relations,
        relationship_get_relation_definitions,
        relationship_get_relation_types,
        relationship_show_graph_on_dataset_read,
        relationship_show_graph_on_read,
        relationship_show_graph_on_group_about,
        relationship_show_graph_on_organization_about,
    ]
    return {f.__name__: f for f in helper_functions}


def relationship_has_relations(pkg_type: str) -> bool:
    return bool(utils.get_relations_info(pkg_type))


def relationship_get_relation_types(pkg_type: str) -> list[str]:
    relation_types: list[str] = []

    for _, _, relation_type in utils.get_relations_info(pkg_type):
        if relation_type not in relation_types:
            relation_types.append(relation_type)

    return relation_types


def relationship_get_relation_definitions() -> dict[str, dict[str, str | None]]:
    definitions = {
        "related_to": {"label": tk._("Related to"), "color": None},
        "child_of": {"label": tk._("Child of"), "color": None},
        "parent_of": {"label": tk._("Parent of"), "color": None},
    }

    for relation_type in relation_types.get_relation_types():
        definitions.setdefault(
            relation_type,
            {
                "label": relation_type.replace("_", " ").title(),
                "color": None,
            },
        )

    for relation_type, metadata in relation_types.get_relation_type_metadata().items():
        definitions.setdefault(relation_type, {"label": relation_type, "color": None})
        if metadata.get("label"):
            definitions[relation_type]["label"] = metadata["label"]
        if metadata.get("color"):
            definitions[relation_type]["color"] = metadata["color"]

    return definitions


def relationship_has_existing_relations(subject_id: str) -> bool:
    subject_name = utils.entity_name_by_id(subject_id)
    conditions = [Relationship.subject_id == subject_id]

    if subject_name:
        conditions.append(Relationship.subject_id == subject_name)

    return (
        model.Session.query(Relationship.id)
        .filter(sa.or_(*conditions))
        .limit(1)
        .scalar()
        is not None
    )


def relationship_show_graph_on_dataset_read() -> bool:
    return config.show_relationship_graph_on_dataset_read()


def relationship_show_graph_on_read() -> bool:
    return relationship_show_graph_on_dataset_read()


def relationship_show_graph_on_group_about() -> bool:
    return config.show_relationship_graph_on_group_about()


def relationship_show_graph_on_organization_about() -> bool:
    return config.show_relationship_graph_on_organization_about()
