import pytest

import ckan.plugins as p
from ckan.tests import factories
from ckan.tests.helpers import call_action


@pytest.mark.ckan_config("ckan.plugins", "relationship")
@pytest.mark.usefixtures("with_plugins")
def test_plugin_registers_actions_helpers_and_validators():
    plugin = p.get_plugin("relationship")

    assert plugin is not None
    assert p.plugin_loaded("relationship")
    assert "relationship_relation_create" in plugin.get_actions()
    assert "relationship_relation_delete" in plugin.get_actions()
    assert "relationship_get_entity_list" in plugin.get_actions()
    assert "relationship_get_entity_list" in plugin.get_helpers()
    assert "relationship_related_entity" in plugin.get_validators()


@pytest.mark.ckan_config("ckan.plugins", "relationship relationship_graph")
@pytest.mark.usefixtures("with_plugins")
def test_relationship_graph_plugin_registers_optional_graph_features():
    plugin = p.get_plugin("relationship_graph")

    assert plugin is not None
    assert p.plugin_loaded("relationship_graph")
    assert "relationship_graph" in plugin.get_actions()
    assert "relationship_get_relation_definitions" in plugin.get_helpers()
    assert "relationship_get_relation_types" in plugin.get_helpers()
    assert "relationship_has_existing_relations" in plugin.get_helpers()
    assert "relationship_show_graph_on_dataset_read" in plugin.get_helpers()
    assert "relationship_show_graph_on_read" in plugin.get_helpers()
    assert "relationship_show_graph_on_group_about" in plugin.get_helpers()
    assert "relationship_show_graph_on_organization_about" in plugin.get_helpers()
    helper = plugin.get_helpers()["relationship_get_relation_types"]
    assert set(helper("package-with-relationship")) == {
        "related_to",
        "child_of",
        "parent_of",
    }


@pytest.mark.usefixtures("clean_db")
def test_before_dataset_index_moves_relationship_ids_to_vocab_field():
    subject = factories.Dataset(type="package-with-relationship")
    related = factories.Dataset(type="package-with-relationship")

    call_action(
        "relationship_relation_create",
        {"ignore_auth": True},
        subject_id=subject["id"],
        object_id=related["id"],
        relation_type="related_to",
    )

    plugin = p.get_plugin("relationship")
    indexed = plugin.before_dataset_index(
        {
            "id": subject["id"],
            "type": "package-with-relationship",
            "related_packages": ["stale-value"],
        }
    )

    assert indexed["vocab_related_packages"] == [related["id"]]
    assert "related_packages" not in indexed
