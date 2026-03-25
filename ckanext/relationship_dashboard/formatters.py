from __future__ import annotations

from markupsafe import escape

import ckan.plugins.toolkit as tk

from ckanext.tables.shared import FormatterResult, Options, Value, formatters

ENTITY_ROUTE_MAP = {
    "group": "group.read",
    "organization": "organization.read",
    "package": "dataset.read",
}


class EntityLinkFormatter(formatters.BaseFormatter):
    def format(self, value: Value, options: Options) -> FormatterResult:
        if not value:
            return ""

        entity_id = self.initial_row.get(options.get("entity_id_field", ""))
        entity_kind = self.initial_row.get(options.get("entity_kind_field", ""))

        if not entity_id or entity_kind not in ENTITY_ROUTE_MAP:
            return str(escape(value))

        url = escape(tk.h.url_for(ENTITY_ROUTE_MAP[entity_kind], id=entity_id))

        return tk.literal(f"<a href='{url}'>{escape(value)}</a>")
