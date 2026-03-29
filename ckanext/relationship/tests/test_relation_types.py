from __future__ import annotations

import pytest

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.tests import factories
from ckan.tests.helpers import call_action


@pytest.mark.ckan_config("ckan.plugins", "relationship")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_action_create_accepts_plugin_provided_relation_type():
    subject = factories.Dataset()
    object_ = factories.Dataset()

    result = call_action(
        "relationship_relation_create",
        {"ignore_auth": True},
        subject_id=subject["id"],
        object_id=object_["id"],
        relation_type="depends_on",
    )

    assert result[0]["relation_type"] == "depends_on"
    assert result[1]["relation_type"] == "required_by"


@pytest.mark.ckan_config(
    "ckan.plugins", "relationship relationship_graph scheming_datasets"
)
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_graph_accepts_plugin_provided_symmetric_relation_type():
    subject = factories.Dataset(type="package-with-relationship")
    object_ = factories.Dataset(type="package-with-relationship")

    call_action(
        "relationship_relation_create",
        {"ignore_auth": True},
        subject_id=subject["id"],
        object_id=object_["id"],
        relation_type="references",
    )

    result = call_action(
        "relationship_graph",
        {"ignore_auth": True},
        object_id=subject["id"],
        relation_types=["references"],
    )

    assert len(result["edges"]) == 1
    assert result["edges"][0]["relation_type"] == "references"
    assert result["edges"][0]["directed"] is False


@pytest.mark.ckan_config("ckan.plugins", "relationship relationship_graph")
@pytest.mark.usefixtures("with_plugins")
def test_graph_helper_exposes_custom_relation_labels_and_colors():
    plugin = p.get_plugin("relationship_graph")

    definitions = plugin.get_helpers()["relationship_get_relation_definitions"]()

    assert definitions["depends_on"]["label"] == "Depends on"
    assert definitions["depends_on"]["color"] == "#7b61ff"
    assert definitions["references"]["label"] == "References"
    assert definitions["references"]["color"] == "#2a9d8f"


@pytest.mark.ckan_config("ckan.plugins", "relationship relationship_graph")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_graph_snippet_includes_custom_relation_definitions(test_request_context):
    dataset = factories.Dataset(type="package-with-relationship")

    with test_request_context(f"/dataset/{dataset['name']}"):
        html = tk.render(
            "relationship_graph/snippets/graph.html",
            extra_vars={
                "object_id": dataset["id"],
                "object_entity": "package",
                "object_type": dataset["type"],
            },
        )

    assert "depends_on" in html
    assert "Depends on" in html
    assert "#7b61ff" in html
