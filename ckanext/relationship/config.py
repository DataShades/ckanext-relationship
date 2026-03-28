from __future__ import annotations

import ckan.plugins.toolkit as tk

CONFIG_VIEWS_WITHOUT_RELATIONSHIPS = (
    "ckanext.relationship.views_without_relationships_in_package_show"
)
CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_READ = (
    "ckanext.relationship.show_relationship_graph_on_read"
)
CONFIG_ASYNC_PACKAGE_INDEX_REBUILD = "ckanext.relationship.async_package_index_rebuild"
CONFIG_REDIS_QUEUE_NAME = "ckanext.relationship.redis_queue_name"


def views_without_relationships_in_package_show() -> list[str]:
    return tk.config[CONFIG_VIEWS_WITHOUT_RELATIONSHIPS]


def show_relationship_graph_on_read() -> bool:
    return tk.config[CONFIG_SHOW_RELATIONSHIP_GRAPH_ON_READ]


def async_package_index_rebuild() -> bool:
    return tk.config[CONFIG_ASYNC_PACKAGE_INDEX_REBUILD]


def redis_queue_name() -> str:
    return tk.config[CONFIG_REDIS_QUEUE_NAME]
