from __future__ import annotations

from ckanext.relationship import config, utils


def get_helpers():
    helper_functions = [
        relationship_has_relations,
        relationship_get_relation_types,
        relationship_show_graph_on_read,
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


def relationship_show_graph_on_read() -> bool:
    return config.show_relationship_graph_on_read()
