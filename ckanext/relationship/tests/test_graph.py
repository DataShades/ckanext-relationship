import json
from pathlib import Path

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests import factories
from ckan.tests.helpers import call_action


@pytest.mark.ckan_config(
    "ckan.plugins", "relationship relationship_graph scheming_datasets"
)
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRelationshipGraphViews:
    def test_graph_endpoint_returns_graph_json(self, app):
        subject = factories.Dataset(type="package-with-relationship")
        related = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            subject_id=subject["id"],
            object_id=related["id"],
            relation_type="related_to",
        )

        response = app.get(
            "/api/2/util/relationships/graph",
            params={
                "object_id": subject["id"],
                "relation_types": "related_to",
            },
            status=200,
        )
        payload = json.loads(response.body)

        assert payload["meta"]["depth"] == 1
        assert {
            node["entity_id"] for node in payload["nodes"] if node["entity_id"]
        } == {
            subject["id"],
            related["id"],
        }
        assert len(payload["edges"]) == 1
        assert payload["edges"][0]["directed"] is False

    def test_graph_endpoint_returns_404_for_missing_center(self, app):
        response = app.get(
            "/api/2/util/relationships/graph",
            params={"object_id": "missing-dataset"},
            status=404,
        )
        payload = json.loads(response.body)

        assert payload["success"] is False
        assert "missing-dataset" in payload["error"]["message"]

    def test_graph_endpoint_enforces_dataset_read_permissions(self, app):
        organization = factories.Organization()
        private_dataset = factories.Dataset(
            type="package-with-relationship",
            owner_org=organization["id"],
            private=True,
        )

        response = app.get(
            "/api/2/util/relationships/graph",
            params={"object_id": private_dataset["id"]},
            status=403,
        )
        payload = json.loads(response.body)

        assert payload["success"] is False


@pytest.mark.ckan_config(
    "ckan.plugins", "relationship relationship_graph scheming_datasets"
)
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRelationshipGraphTemplates:
    def test_graph_snippet_renders_assets_and_data_attributes(
        self, app, test_request_context
    ):
        dataset = factories.Dataset(type="package-with-relationship")

        with test_request_context(f"/dataset/{dataset['name']}"):
            html = tk.render(
                "relationship_graph/snippets/graph.html",
                extra_vars={
                    "object_id": dataset["id"],
                    "object_entity": "package",
                    "object_type": dataset["type"],
                    "depth": 2,
                    "max_nodes": 80,
                    "relation_types": ["related_to"],
                },
            )

        assert 'data-module="relationship-graph"' in html
        assert f'data-object-id="{dataset["id"]}"' in html
        assert "/api/2/util/relationships/graph" in html
        assert 'data-graph-role="labels-toggle"' in html
        assert 'data-graph-role="download"' in html
        assert 'data-graph-role="legend"' in html
        assert 'data-graph-role="tooltip"' in html
        assert html.index('data-graph-role="viewport"') < html.index(
            'data-graph-role="depth"'
        )

    def test_graph_bundles_are_declared_separately(self):
        webassets = Path(
            "/home/aleks/Projects/relationship/src/ckanext-relationship/"
            "ckanext/relationship_graph/assets/webassets.yml"
        ).read_text()

        assert "relationship-graph-vendor:" in webassets
        assert "relationship-graph-js:" in webassets
        assert "relationship-graph-css:" in webassets
        assert "js/vendor/cytoscape.js" in webassets

    def test_dataset_page_renders_graph_snippet(self, app):
        dataset = factories.Dataset(type="package-with-relationship")

        response = app.get(f"/dataset/{dataset['name']}", status=200)

        assert 'data-module="relationship-graph"' in response
        assert "relationship-graph-section" in response
        assert "/api/2/util/relationships/graph" in response
        assert "relationship-graph.css" in response
        assert "relationship-graph.js" in response
        assert (
            '<th scope="row" class="dataset-label">Relationship graph</th>'
            not in response
        )


@pytest.mark.ckan_config(
    "ckan.plugins", "relationship relationship_graph scheming_datasets"
)
@pytest.mark.ckan_config("ckanext.relationship.show_relationship_graph_on_read", False)
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRelationshipGraphReadPageConfig:
    def test_dataset_page_does_not_render_graph_when_disabled_by_config(self, app):
        dataset = factories.Dataset(type="package-with-relationship")

        response = app.get(f"/dataset/{dataset['name']}", status=200)

        assert 'data-module="relationship-graph"' not in response
        assert "relationship-graph-section" not in response


@pytest.mark.ckan_config("ckan.plugins", "relationship scheming_datasets")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRelationshipGraphOptionalPlugin:
    def test_graph_endpoint_is_not_registered_without_plugin(self, app):
        app.get("/api/2/util/relationships/graph", status=404)

    def test_dataset_page_does_not_render_graph_without_plugin(self, app):
        dataset = factories.Dataset(type="package-with-relationship")

        response = app.get(f"/dataset/{dataset['name']}", status=200)

        assert 'data-module="relationship-graph"' not in response
