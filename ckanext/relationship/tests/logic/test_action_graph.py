import pytest

import ckan.plugins.toolkit as tk
from ckan import logic, model
from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.relationship.model.relationship import Relationship
from ckanext.relationship_graph.logic import action as graph_action


def _graph(object_id: str, **kwargs):
    return call_action("relationship_graph", object_id=object_id, **kwargs)


def _relate(subject_id: str, object_id: str, relation_type: str):
    call_action(
        "relationship_relation_create",
        subject_id=subject_id,
        object_id=object_id,
        relation_type=relation_type,
    )


def _insert_legacy_relation(
    subject_id: str,
    object_id: str,
    relation_type: str,
) -> None:
    reverse_relation_type = Relationship.reverse_relation_type[relation_type]
    model.Session.add(
        Relationship(
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )
    )
    model.Session.add(
        Relationship(
            subject_id=object_id,
            object_id=subject_id,
            relation_type=reverse_relation_type,
        )
    )
    model.Session.commit()


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config(
    "ckan.plugins", "relationship relationship_graph scheming_datasets"
)
@pytest.mark.usefixtures("with_plugins")
class TestRelationshipGraphAction:
    def test_depth_1_includes_only_direct_neighbors(self):
        alpha = factories.Dataset(type="package-with-relationship")
        beta = factories.Dataset(type="package-with-relationship")
        gamma = factories.Dataset(type="package-with-relationship")

        _relate(alpha["id"], beta["id"], "related_to")
        _relate(beta["id"], gamma["id"], "related_to")

        result = _graph(alpha["id"], depth=1, relation_types=["related_to"])
        node_ids = {node["entity_id"] for node in result["nodes"] if node["entity_id"]}

        assert node_ids == {alpha["id"], beta["id"]}
        assert len(result["edges"]) == 1
        assert result["edges"][0]["directed"] is False
        assert result["meta"]["depth"] == 1
        assert result["meta"]["truncated"] is False

    def test_depth_2_includes_second_level_neighbors(self):
        alpha = factories.Dataset(type="package-with-relationship")
        beta = factories.Dataset(type="package-with-relationship")
        gamma = factories.Dataset(type="package-with-relationship")

        _relate(alpha["id"], beta["id"], "related_to")
        _relate(beta["id"], gamma["id"], "related_to")

        result = _graph(alpha["id"], depth=2, relation_types=["related_to"])
        node_ids = {node["entity_id"] for node in result["nodes"] if node["entity_id"]}

        assert node_ids == {alpha["id"], beta["id"], gamma["id"]}

    def test_cycle_does_not_duplicate_nodes(self):
        alpha = factories.Dataset(type="package-with-relationship")
        beta = factories.Dataset(type="package-with-relationship")
        gamma = factories.Dataset(type="package-with-relationship")

        _relate(alpha["id"], beta["id"], "related_to")
        _relate(beta["id"], gamma["id"], "related_to")
        _relate(gamma["id"], alpha["id"], "related_to")

        result = _graph(alpha["id"], depth=3, relation_types=["related_to"])
        node_ids = {node["entity_id"] for node in result["nodes"] if node["entity_id"]}

        assert node_ids == {alpha["id"], beta["id"], gamma["id"]}
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 3

    def test_unresolved_name_node_is_returned_when_requested(self):
        subject = factories.Dataset(type="package-with-relationship")

        _insert_legacy_relation(subject["id"], "remote-dataset-name", "related_to")

        result = _graph(subject["id"], relation_types=["related_to"])
        unresolved = next(
            node for node in result["nodes"] if node["name"] == "remote-dataset-name"
        )

        assert unresolved["resolved"] is False
        assert unresolved["url"] is None
        assert unresolved["entity"] == "package"
        assert unresolved["entity_type"] == "dataset"

    def test_max_nodes_truncates_graph(self):
        alpha = factories.Dataset(type="package-with-relationship")
        beta = factories.Dataset(type="package-with-relationship")
        gamma = factories.Dataset(type="package-with-relationship")
        delta = factories.Dataset(type="package-with-relationship")

        _relate(alpha["id"], beta["id"], "related_to")
        _relate(beta["id"], gamma["id"], "related_to")
        _relate(gamma["id"], delta["id"], "related_to")

        result = _graph(alpha["id"], depth=3, max_nodes=3)
        node_ids = {node["entity_id"] for node in result["nodes"] if node["entity_id"]}

        assert len(result["nodes"]) == 3
        assert delta["id"] not in node_ids
        assert result["meta"]["truncated"] is True

    def test_relation_type_filter_limits_edges_and_nodes(self):
        alpha = factories.Dataset(type="package-with-relationship")
        beta = factories.Dataset(type="package-with-relationship")
        gamma = factories.Dataset(type="package-with-relationship")

        _relate(alpha["id"], beta["id"], "related_to")
        _relate(alpha["id"], gamma["id"], "child_of")

        result = _graph(alpha["id"], relation_types=["related_to"])
        node_ids = {node["entity_id"] for node in result["nodes"] if node["entity_id"]}

        assert beta["id"] in node_ids
        assert gamma["id"] not in node_ids
        assert {edge["relation_type"] for edge in result["edges"]} == {"related_to"}

    def test_empty_graph_returns_only_center_node(self):
        subject = factories.Dataset(type="package-with-relationship")

        result = _graph(subject["id"])

        assert result["edges"] == []
        assert result["meta"]["truncated"] is False
        assert result["nodes"] == [
            {
                "id": f"package:{subject['id']}",
                "entity_id": subject["id"],
                "name": subject["name"],
                "title": subject["title"],
                "entity": "package",
                "entity_type": "package-with-relationship",
                "resolved": True,
                "url": f"/dataset/{subject['name']}",
                "level": 0,
                "is_center": True,
            }
        ]

    def test_graph_caches_repeated_entity_record_lookups(self, monkeypatch):
        alpha = factories.Dataset(type="package-with-relationship")
        beta = factories.Dataset(type="package-with-relationship")
        gamma = factories.Dataset(type="package-with-relationship")

        _relate(alpha["id"], beta["id"], "related_to")
        _relate(beta["id"], gamma["id"], "related_to")
        _relate(gamma["id"], alpha["id"], "related_to")

        lookup_calls: list[tuple[str, str]] = []
        original = graph_action._load_entity_record

        def counting_loader(session, entity, identifier):
            lookup_calls.append((entity, identifier))
            return original(session, entity, identifier)

        monkeypatch.setattr(graph_action, "_load_entity_record", counting_loader)

        _graph(alpha["id"], depth=3, relation_types=["related_to"])

        assert lookup_calls.count(("package", alpha["id"])) == 1
        assert lookup_calls.count(("package", beta["id"])) == 1
        assert lookup_calls.count(("package", gamma["id"])) == 1

    def test_graph_batches_relationship_queries_per_frontier_level(self, monkeypatch):
        alpha = factories.Dataset(type="package-with-relationship")
        beta = factories.Dataset(type="package-with-relationship")
        gamma = factories.Dataset(type="package-with-relationship")
        delta = factories.Dataset(type="package-with-relationship")
        epsilon = factories.Dataset(type="package-with-relationship")

        _relate(alpha["id"], beta["id"], "related_to")
        _relate(alpha["id"], gamma["id"], "related_to")
        _relate(beta["id"], delta["id"], "related_to")
        _relate(gamma["id"], epsilon["id"], "related_to")

        relationship_queries: list[frozenset[str]] = []
        original = graph_action._get_graph_relationships

        def counting_relationships(
            session, lookup_ids, relation_types, include_reverse
        ):
            relationship_queries.append(frozenset(lookup_ids))
            return original(session, lookup_ids, relation_types, include_reverse)

        monkeypatch.setattr(
            graph_action,
            "_get_graph_relationships",
            counting_relationships,
        )

        _graph(alpha["id"], depth=2, relation_types=["related_to"])

        assert len(relationship_queries) == 2
        assert {alpha["id"], alpha["name"]}.issubset(relationship_queries[0])
        assert {
            beta["id"],
            beta["name"],
            gamma["id"],
            gamma["name"],
        }.issubset(relationship_queries[1])

    def test_nonexistent_center_raises_not_found(self):
        with pytest.raises(logic.NotFound):
            _graph("missing-dataset")

    def test_private_center_requires_read_access(self):
        organization = factories.Organization()
        dataset = factories.Dataset(
            type="package-with-relationship",
            owner_org=organization["id"],
            private=True,
        )

        with pytest.raises(logic.NotAuthorized):
            tk.get_action("relationship_graph")(
                {
                    "model": model,
                    "session": model.Session,
                    "user": "",
                },
                {
                    "object_id": dataset["id"],
                },
            )

    def test_depth_and_max_nodes_are_validated(self):
        subject = factories.Dataset(type="package-with-relationship")

        with pytest.raises(tk.ValidationError):
            _graph(subject["id"], depth=5)

        with pytest.raises(tk.ValidationError):
            _graph(subject["id"], max_nodes=301)
