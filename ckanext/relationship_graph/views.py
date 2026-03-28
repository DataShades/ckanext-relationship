from __future__ import annotations

from flask import Blueprint, jsonify

import ckan.plugins.toolkit as tk
from ckan import logic


def get_blueprints():
    return [
        relationship_graph,
    ]


relationship_graph = Blueprint("relationship_graph", __name__)


def _json_error_response(status_code: int, message: str):
    return (
        jsonify(
            {
                "success": False,
                "error": {
                    "message": message,
                },
            }
        ),
        status_code,
    )


@relationship_graph.route("/api/2/util/relationships/graph")
def relationship_graph_api():
    request_args = tk.request.args
    relation_types: str | list[str] | None = request_args.getlist("relation_types")

    if not relation_types:
        relation_types = request_args.get("relation_types")
    elif len(relation_types) == 1:
        relation_types = relation_types[0]

    try:
        result = tk.get_action("relationship_graph")(
            {},
            {
                "object_id": request_args.get("object_id"),
                "object_entity": request_args.get("object_entity"),
                "object_type": request_args.get("object_type"),
                "depth": request_args.get("depth"),
                "relation_types": relation_types,
                "max_nodes": request_args.get("max_nodes"),
                "include_unresolved": request_args.get("include_unresolved"),
                "include_reverse": request_args.get("include_reverse"),
                "with_titles": request_args.get("with_titles"),
            },
        )
    except tk.ValidationError as err:
        return _json_error_response(400, str(err))
    except logic.NotAuthorized as err:
        return _json_error_response(403, str(err))
    except logic.NotFound as err:
        return _json_error_response(404, str(err))

    return jsonify(result)
