from __future__ import annotations

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.common import CKANConfig

from ckanext.relationship_graph import helpers, views
from ckanext.relationship_graph.logic import action, auth


class RelationshipGraphPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IBlueprint)

    def update_config(self, config_: CKANConfig) -> None:
        tk.add_template_directory(config_, "templates")
        tk.add_resource("assets", "relationship_graph")

    def get_actions(self):
        return action.get_actions()

    def get_auth_functions(self):
        return auth.get_auth_functions()

    def get_helpers(self):
        return helpers.get_helpers()

    def get_blueprint(self):
        return views.get_blueprints()
