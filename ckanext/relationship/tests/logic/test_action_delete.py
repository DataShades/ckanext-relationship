import pytest

from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.relationship.model.relationship import Relationship


@pytest.mark.usefixtures("clean_db")
class TestRelationDelete:
    def test_relation_delete(self):
        subject_dataset = factories.Dataset()
        object_dataset = factories.Dataset()

        subject_id = subject_dataset["id"]
        object_id = object_dataset["id"]
        relation_type = "related_to"

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )

        result = call_action(
            "relationship_relation_delete",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )

        assert result[0]["subject_id"] == subject_id
        assert result[0]["object_id"] == object_id
        assert result[0]["relation_type"] == relation_type

        assert result[1]["subject_id"] == object_id
        assert result[1]["object_id"] == subject_id
        assert result[1]["relation_type"] == relation_type

    def test_relation_deleted_from_db(self):
        subject_dataset = factories.Dataset()
        object_dataset = factories.Dataset()

        subject_id = subject_dataset["id"]
        object_id = object_dataset["id"]
        relation_type = "related_to"

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )

        call_action(
            "relationship_relation_delete",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )

        relation_straight = Relationship.by_object_id(
            subject_id,
            object_id,
            relation_type,
        )
        relation_reverse = Relationship.by_object_id(
            object_id,
            subject_id,
            relation_type,
        )

        assert not relation_straight
        assert not relation_reverse

    def test_relation_delete_without_relation_type_removes_all_matches(self):
        subject_dataset = factories.Dataset()
        object_dataset = factories.Dataset()

        subject_id = subject_dataset["id"]
        object_id = object_dataset["id"]

        for relation_type in ("related_to", "child_of"):
            call_action(
                "relationship_relation_create",
                {"ignore_auth": True},
                subject_id=subject_id,
                object_id=object_id,
                relation_type=relation_type,
            )

        call_action(
            "relationship_relation_delete",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object_id,
        )

        assert (
            call_action(
                "relationship_relations_list",
                {"ignore_auth": True},
                subject_id=subject_id,
            )
            == []
        )

    def test_relation_delete_after_dataset_delete(self):
        subject_dataset = factories.Dataset()
        object_dataset = factories.Dataset()

        subject_id = subject_dataset["id"]
        object_id = object_dataset["id"]
        relation_type = "related_to"

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )

        call_action("package_delete", {"ignore_auth": True}, id=subject_id)

        relation_straight = Relationship.by_object_id(
            subject_id,
            object_id,
            relation_type,
        )
        relation_reverse = Relationship.by_object_id(
            object_id,
            subject_id,
            relation_type,
        )

        assert not relation_straight
        assert not relation_reverse
