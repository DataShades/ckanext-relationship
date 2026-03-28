import pytest

from ckan.tests import factories
from ckan.tests.helpers import call_action


@pytest.mark.usefixtures("clean_db")
class TestRelationList:
    @pytest.mark.parametrize(
        ("subject_factory", "object_factory", "object_entity", "object_type"),
        [
            (factories.Dataset, factories.Dataset, "package", "dataset"),
            (factories.Dataset, factories.Organization, "organization", "organization"),
            (factories.Dataset, factories.Group, "group", "group"),
            (factories.Organization, factories.Dataset, "package", "dataset"),
            (
                factories.Organization,
                factories.Organization,
                "organization",
                "organization",
            ),
            (factories.Organization, factories.Group, "group", "group"),
            (factories.Group, factories.Dataset, "package", "dataset"),
            (factories.Group, factories.Organization, "organization", "organization"),
            (factories.Group, factories.Group, "group", "group"),
        ],
    )
    def test_relation_list(
        self,
        subject_factory,
        object_factory,
        object_entity: str,
        object_type: str,
    ):
        subject = subject_factory()
        object_ = object_factory()

        subject_id = subject["id"]
        object_id = object_["id"]
        relation_type = "related_to"

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )

        result = call_action(
            "relationship_relations_list",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_entity=object_entity,
            object_type=object_type,
            relation_type=relation_type,
        )

        assert result[0]["subject_id"] == subject_id
        assert result[0]["object_id"] == object_id
        assert result[0]["relation_type"] == relation_type

    def test_relation_list_empty(self):
        subject_dataset = factories.Dataset()

        subject_id = subject_dataset["id"]
        relation_type = "related_to"

        result = call_action(
            "relationship_relations_list",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_entity="package",
            object_type="dataset",
            relation_type=relation_type,
        )

        assert result == []

    def test_relation_list_after_dataset_delete(self):
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

        result = call_action(
            "relationship_relations_list",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_entity="package",
            object_type="dataset",
            relation_type=relation_type,
        )

        assert result == []


@pytest.mark.usefixtures("clean_db")
class TestRelationsIdsList:
    def test_relations_ids_list(self):
        subject_dataset = factories.Dataset()
        object1_dataset = factories.Dataset()
        object2_dataset = factories.Dataset()

        subject_id = subject_dataset["id"]
        object1_id = object1_dataset["id"]
        object2_id = object2_dataset["id"]
        relation_type = "related_to"

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object1_id,
            relation_type=relation_type,
        )

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_id=object2_id,
            relation_type=relation_type,
        )

        result = call_action(
            "relationship_relations_ids_list",
            {"ignore_auth": True},
            subject_id=subject_id,
            object_entity="package",
            object_type="dataset",
            relation_type=relation_type,
        )

        assert object1_id in result
        assert object2_id in result
