from __future__ import annotations

from typing import Any

from flask import Blueprint, make_response

import ckan.plugins.toolkit as tk

from ckanext.relationship import utils

BATCH_SIZE_DEFAULT = 20


def get_blueprints():
    return [
        relationships,
    ]


relationships = Blueprint("relationships", __name__)


@relationships.route("/api/2/util/relationships/autocomplete")
def relationships_autocomplete():
    request_args = tk.request.args
    return tk.get_action("relationship_autocomplete")(
        {},
        {
            "incomplete": request_args.get("incomplete"),
            "current_entity_id": request_args.get("current_entity_id"),
            "entity_type": request_args.get("entity_type", "dataset"),
            "updatable_only": tk.asbool(request_args.get("updatable_only")),
            "owned_only": tk.asbool(request_args.get("owned_only")),
            "check_sysadmin": tk.asbool(request_args.get("check_sysadmin")),
            "format_autocomplete_helper": request_args.get(
                "format_autocomplete_helper",
            ),
        },
    )


def _search_packages_page(
    context: dict[str, Any], fq: str, start: int, rows: int
) -> tuple[list[dict[str, Any]], int]:
    """Searches for packages using the package_search action."""
    data = {
        "q": "*:*",
        "fq": fq,
        "start": start,
        "rows": rows,
        "include_private": True,
        "sort": "title_string asc, name asc, id asc",
    }
    out = tk.get_action("package_search")({}, data) or {}
    return out.get("results", []), out.get("count", 0)


@relationships.route("/relationship/section")
def related_batch():
    """Renders a section of related packages."""
    pkg_id = tk.request.args["pkg_id"]
    object_type = tk.request.args["object_type"]
    relation_type = tk.request.args["relation_type"]
    start = int(tk.request.args.get("start", 0))
    page_size = int(tk.request.args.get("size", BATCH_SIZE_DEFAULT))

    object_ids = tk.get_action("relationship_relations_ids_list")(
        {},
        {
            "subject_id": pkg_id,
            "object_entity": "package",
            "object_type": object_type,
            "relation_type": relation_type,
        },
    )

    if not object_ids:
        return ("", 204)

    fq = utils.build_fq_for_object_ids(object_ids)
    packages, total = _search_packages_page({}, fq, start=start, rows=page_size)
    if not packages and start == 0:
        return ("", 204)

    html = tk.render(
        "snippets/relationship_related_batch.html",
        extra_vars={
            "packages": packages,
            "has_more": (start + page_size) < total,
            "next_start": start + page_size,
            "page_size": page_size,
            "pkg_id": pkg_id,
            "object_type": object_type,
            "relation_type": relation_type,
        },
    )
    return make_response(html)
