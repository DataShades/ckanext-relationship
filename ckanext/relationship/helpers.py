from __future__ import annotations

import json
from typing import Any

import ckan.plugins.toolkit as tk
from ckan import authz
from ckan.lib.search.query import solr_literal


def get_helpers():
    helper_functions = [
        relationship_get_entity_list,
        relationship_get_current_relations_list,
        relationship_get_selected_json,
        relationship_get_choices_for_related_entity_field,
        relationship_format_autocomplete,
    ]
    return {f.__name__: f for f in helper_functions}


def relationship_get_entity_list(
    entity: str,
    entity_type: str,
    entity_query: dict[str, Any] | None = None,
    include_private: bool = True,
) -> list[dict[str, str]]:
    """Return ids list of specified entity (entity, entity_type)."""

    if entity == "package":
        params = (
            entity_query
            if entity_query
            else {
                "fq": f"type:{entity_type}",
                "rows": 1000,
                "include_private": include_private,
            }
        )
        entity_list = tk.get_action("package_search")(
            {},
            params,
        )
        entity_list = entity_list["results"]
    else:
        params = (
            entity_query
            if entity_query
            else {"entity": entity, "entity_type": entity_type}
        )
        entity_list = tk.get_action("relationship_get_entity_list")(
            {},
            params,
        )
        entity_list = [
            {"id": id, "name": name, "title": title} for id, name, title in entity_list
        ]
    return entity_list


def relationship_get_current_relations_list(
    data: dict[str, Any], field: dict[str, Any]
) -> list[str]:
    """Pull existing relations for form_snippet and display_snippet."""
    subject_id = field.get("id")
    subject_name = field.get("name")
    if not subject_id and not subject_name:
        return []
    related_entity = data["related_entity"]
    related_entity_type = data["related_entity_type"]
    relation_type = data["relation_type"]

    current_relation_by_id: list[str] = []
    current_relation_by_name: list[str] = []

    if subject_id:
        current_relation_by_id = tk.get_action("relationship_relations_ids_list")(
            {},
            {
                "subject_id": subject_id,
                "object_entity": related_entity,
                "object_type": related_entity_type,
                "relation_type": relation_type,
            },
        )
    if subject_name:
        current_relation_by_name = tk.get_action("relationship_relations_ids_list")(
            {},
            {
                "subject_id": subject_name,
                "object_entity": related_entity,
                "object_type": related_entity_type,
                "relation_type": relation_type,
            },
        )
    return current_relation_by_id + current_relation_by_name


def relationship_get_selected_json(selected_ids: list[str] | None = None) -> str:
    if not selected_ids:
        return json.dumps([])

    selected_pkgs = []
    search = tk.get_action("package_search")
    rows = 100
    start = 0
    fq = "id:({})".format(" OR ".join(map(solr_literal, selected_ids)))
    while True:
        result = search(
            {},
            {
                "include_private": True,
                "fq": fq,
                "rows": rows,
                "start": start,
                "fl": "id,name,title",
            },
        )
        selected_pkgs.extend(
            [
                {"name": pkg_dict["id"], "title": pkg_dict["title"]}
                for pkg_dict in result["results"]
            ]
        )

        if not result["results"]:
            break
        start += rows

    return json.dumps(selected_pkgs)


def relationship_get_choices_for_related_entity_field(
    field: dict[str, Any],
    current_entity_id: str | None,
) -> list[tuple[str, str | None]]:
    entities = relationship_get_entity_list(
        field["related_entity"],
        field["related_entity_type"],
        field.get("related_entity_query"),
    )

    choices: list[tuple[str, str | None]] = []

    for entity in entities:
        if entity["id"] == current_entity_id:
            continue

        if field.get("updatable_only", False) and not tk.h.check_access(
            field["related_entity"] + "_update",
            {"id": entity["id"]},
        ):
            continue

        if (
            field.get("owned_only", False)
            and not authz.is_sysadmin(tk.current_user.id)
            and field["related_entity"] == "package"
            and tk.current_user.id != entity["creator_user_id"]
        ):
            continue

        choices.append((entity["id"], entity.get("title") or entity.get("name")))

    # pyright: ignore[reportArgumentType, reportCallIssue]
    choices.sort(key=lambda x: x[1])
    return choices


def relationship_format_autocomplete(packages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ResultSet": {
            "Result": [
                {
                    "name": pkg["id"],
                    "title": pkg["title"],
                }
                for pkg in packages
            ],
        },
    }
