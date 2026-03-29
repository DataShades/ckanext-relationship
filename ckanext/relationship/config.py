from __future__ import annotations

import ckan.plugins.toolkit as tk

CONFIG_VIEWS_WITHOUT_RELATIONSHIPS = (
    "ckanext.relationship.views_without_relationships_in_package_show"
)
CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_DATASET_READ = (
    "ckanext.relationship.show_relationship_graph_on_dataset_read"
)
CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_GROUP_ABOUT = (
    "ckanext.relationship.show_relationship_graph_on_group_about"
)
CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_ORGANIZATION_ABOUT = (
    "ckanext.relationship.show_relationship_graph_on_organization_about"
)
CONFIG_ASYNC_PACKAGE_INDEX_REBUILD = "ckanext.relationship.async_package_index_rebuild"
CONFIG_REDIS_QUEUE_NAME = "ckanext.relationship.redis_queue_name"
CONFIG_ALLOW_NAME_BASED_RELATION_CREATE = (
    "ckanext.relationship.allow_name_based_relation_create"
)


def views_without_relationships_in_package_show() -> list[str]:
    return tk.config[CONFIG_VIEWS_WITHOUT_RELATIONSHIPS]


def show_relationship_graph_on_dataset_read() -> bool:
    return tk.config[CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_DATASET_READ]


def show_relationship_graph_on_group_about() -> bool:
    return tk.config[CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_GROUP_ABOUT]


def show_relationship_graph_on_organization_about() -> bool:
    return tk.config[CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_ORGANIZATION_ABOUT]


def async_package_index_rebuild() -> bool:
    return tk.config[CONFIG_ASYNC_PACKAGE_INDEX_REBUILD]


def redis_queue_name() -> str:
    return tk.config[CONFIG_REDIS_QUEUE_NAME]


def allow_name_based_relation_create() -> bool:
    return tk.config[CONFIG_ALLOW_NAME_BASED_RELATION_CREATE]
