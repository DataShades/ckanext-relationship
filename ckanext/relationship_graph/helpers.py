from __future__ import annotations

import sqlalchemy as sa

from ckan import model

from ckanext.relationship import config, utils
from ckanext.relationship.model.relationship import Relationship


def get_helpers():
    helper_functions = [
        relationship_has_relations,
        relationship_has_existing_relations,
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
