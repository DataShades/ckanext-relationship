import json

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.relationship import helpers


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestRelationshipHelpers:
    def test_get_current_relations_list_uses_documented_field_data_order(self):
        subject = factories.Dataset(type="package-with-relationship")
        related = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject["id"],
            object_id=related["id"],
            relation_type="related_to",
        )

        field = {
            "related_entity": "package",
            "related_entity_type": "package-with-relationship",
            "relation_type": "related_to",
        }

        assert helpers.relationship_get_current_relations_list(field, subject) == [
            related["id"]
        ]

    def test_get_selected_json_returns_prepopulated_package_payload(self):
        alpha = factories.Dataset(type="package-with-relationship", title="Alpha")
        beta = factories.Dataset(type="package-with-relationship", title="Beta")

        payload = json.loads(
            helpers.relationship_get_selected_json([beta["id"], alpha["id"]])
        )

        assert payload == [
            {"name": alpha["id"], "title": "Alpha"},
            {"name": beta["id"], "title": "Beta"},
        ]

    def test_get_selected_json_returns_empty_for_non_package_entity(self):
        payload = json.loads(
            helpers.relationship_get_selected_json(
                ["group-identifier"],
                entity="group",
            )
        )

        assert payload == []

    def test_get_choices_for_related_entity_field_skips_current_package(self):
        current = factories.Dataset(type="package-with-relationship", title="Current")
        other = factories.Dataset(type="package-with-relationship", title="Other")

        choices = helpers.relationship_get_choices_for_related_entity_field(
            {
                "related_entity": "package",
                "related_entity_type": "package-with-relationship",
            },
            current["id"],
        )

        assert choices == [(other["id"], "Other")]


@pytest.mark.ckan_config("ckan.plugins", "relationship scheming_datasets")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRelationshipAutocompleteTemplate:
    def test_package_autocomplete_snippet_uses_full_width_controls(
        self, test_request_context
    ):
        field = {
            "field_name": "related_projects",
            "label": "Related projects",
            "form_placeholder": "Start typing",
            "related_entity": "package",
            "related_entity_type": "package-with-relationship",
            "relation_type": "related_to",
        }

        with test_request_context("/dataset/example"):
            html = tk.render(
                "scheming/form_snippets/related_entity_with_autocomplete.html",
                extra_vars={
                    "field": field,
                    "data": {},
                    "errors": {field["field_name"]: []},
                },
            )

        assert "control-full" in html
        assert 'data-module="relationship-autocomplete"' in html
        assert 'data-module-tags="false"' in html

    def test_package_autocomplete_snippet_uses_tags_for_multiple_fields(
        self, test_request_context
    ):
        field = {
            "field_name": "related_projects",
            "label": "Related projects",
            "form_placeholder": "Start typing",
            "related_entity": "package",
            "related_entity_type": "package-with-relationship",
            "relation_type": "related_to",
            "multiple": True,
        }

        with test_request_context("/dataset/example"):
            html = tk.render(
                "scheming/form_snippets/related_entity_with_autocomplete.html",
                extra_vars={
                    "field": field,
                    "data": {},
                    "errors": {field["field_name"]: []},
                },
            )

        assert 'data-module-tags="true"' in html

    def test_package_autocomplete_single_field_keeps_scalar_request_value(
        self, test_request_context
    ):
        field = {
            "field_name": "related_projects",
            "label": "Related projects",
            "form_placeholder": "Start typing",
            "related_entity": "package",
            "related_entity_type": "package-with-relationship",
            "relation_type": "related_to",
        }

        with test_request_context("/dataset/example?related_projects=example-id"):
            html = tk.render(
                "scheming/form_snippets/related_entity_with_autocomplete.html",
                extra_vars={
                    "field": field,
                    "data": {},
                    "errors": {field["field_name"]: []},
                },
            )

        assert 'value="example-id"' in html

    def test_non_package_autocomplete_snippet_falls_back_to_select_widget(
        self, test_request_context
    ):
        field = {
            "field_name": "related_groups",
            "label": "Related groups",
            "related_entity": "group",
            "related_entity_type": "group",
            "relation_type": "related_to",
        }

        with test_request_context("/dataset/example"):
            html = tk.render(
                "scheming/form_snippets/related_entity_with_autocomplete.html",
                extra_vars={
                    "field": field,
                    "data": {},
                    "errors": {field["field_name"]: []},
                },
            )

        assert "control-full" in html
        assert 'data-module="relationship-autocomplete"' not in html
        assert "<select" in html
