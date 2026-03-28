from __future__ import annotations

from typing import Any

from ckan import types
from ckan.plugins import toolkit as tk


def get_auth_functions():
    auth_functions = [
        relationship_graph,
    ]
    return {f.__name__: f for f in auth_functions}


@tk.auth_allow_anonymous_access
def relationship_graph(context: types.Context, data_dict: dict[str, Any]):
    return {"success": True}
