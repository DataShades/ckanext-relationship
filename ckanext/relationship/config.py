from __future__ import annotations

import ckan.plugins.toolkit as tk

CONFIG_VIEWS_WITHOUT_RELATIONSHIPS = (
    "ckanext.relationship.views_without_relationships_in_package_show"
)
CONFIG_ASYNC_PACKAGE_INDEX_REBUILD = "ckanext.relationship.async_package_index_rebuild"
CONFIG_REDIS_QUEUE_NAME = "ckanext.relationship.redis_queue_name"


DEFAULT_VIEWS_WITHOUT_RELATIONSHIPS = ["search", "read"]


def views_without_relationships_in_package_show() -> list[str]:
    return tk.aslist(
        tk.config.get(
            CONFIG_VIEWS_WITHOUT_RELATIONSHIPS,
            DEFAULT_VIEWS_WITHOUT_RELATIONSHIPS,
        ),
    )


def async_package_index_rebuild() -> bool:
    return tk.config[CONFIG_ASYNC_PACKAGE_INDEX_REBUILD]


def redis_queue_name() -> str:
    return tk.config[CONFIG_REDIS_QUEUE_NAME]
