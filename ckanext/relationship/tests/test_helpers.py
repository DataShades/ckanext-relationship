import json

import pytest

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
