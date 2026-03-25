from __future__ import annotations

from flask import Blueprint

import ckan.plugins.toolkit as tk

from ckanext.tables.shared import GenericTableView

from ckanext.relationship_dashboard.table import RelationshipDashboardTable


def get_blueprints():
    return [
        relationship_dashboard,
    ]


relationship_dashboard = Blueprint(
    "relationship_dashboard",
    __name__,
    url_prefix="/ckan-admin/relationships",
)


def before_request() -> None:
    try:
        tk.check_access("sysadmin", {"user": getattr(tk.current_user, "name", None)})
    except tk.NotAuthorized:
        tk.abort(403, tk._("Need to be system administrator to administer"))


relationship_dashboard.before_request(before_request)

relationship_dashboard.add_url_rule(
    "/dashboard",
    view_func=GenericTableView.as_view(
        "dashboard",
        table=RelationshipDashboardTable,
        breadcrumb_label="Relationships",
        page_title="Relationships dashboard",
    ),
)
