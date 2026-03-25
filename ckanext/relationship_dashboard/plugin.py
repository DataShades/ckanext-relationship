from __future__ import annotations

from typing import Any

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan import types
from ckan.common import CKANConfig

from ckanext.relationship_dashboard import views
from ckanext.relationship_dashboard.table import RelationshipDashboardTable


class RelationshipDashboardPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)
    p.implements(p.ISignal)

    def update_config(self, config_: CKANConfig) -> None:
        tk.add_template_directory(config_, "templates")

    def get_blueprint(self):
        return views.get_blueprints()

    def get_signal_subscriptions(self) -> types.SignalMapping:
        return {
            tk.signals.ckanext.signal("ckanext.tables.register_tables"): [
                self.collect_tables
            ],
        }

    def collect_tables(self, sender: None) -> dict[str, type[Any]]:
        return {"relationship": RelationshipDashboardTable}
