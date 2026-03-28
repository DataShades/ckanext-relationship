import pytest

import ckan.plugins.toolkit as tk
from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.relationship.model.relationship import Relationship


@pytest.mark.usefixtures("clean_db")
def test_keep_relation_after_dataset_patch():
    subject_dataset = factories.Dataset(type="package-with-relationship")
    object_dataset = factories.Dataset(type="package-with-relationship")

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
        "package_patch", {"ignore_auth": True}, id=subject_id, title="New title"
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

    assert relation_straight is not None
    assert relation_reverse is not None


@pytest.mark.usefixtures("clean_db")
class TestPackageShow:
    @pytest.mark.parametrize(
        ("path_template", "endpoint_action"),
        [
            ("/dataset", "search"),
            ("/dataset/{name}", "read"),
        ],
    )
    def test_package_show_hides_relationships_on_documented_views(
        self,
        test_request_context,
        path_template: str,
        endpoint_action: str,
    ):
        subject_dataset = factories.Dataset(type="package-with-relationship")
        object_dataset = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_dataset["id"],
            object_id=object_dataset["id"],
            relation_type="related_to",
        )

        with test_request_context(path_template.format(name=subject_dataset["name"])):
            assert tk.get_endpoint() == ("dataset", endpoint_action)
            result = call_action(
                "package_show",
                {"ignore_auth": True},
                id=subject_dataset["id"],
            )

        assert "related_packages" not in result

    def test_package_show_includes_relationships_when_requested(
        self,
        test_request_context,
    ):
        subject_dataset = factories.Dataset(type="package-with-relationship")
        object_dataset = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_dataset["id"],
            object_id=object_dataset["id"],
            relation_type="related_to",
        )

        with test_request_context(f"/dataset/{subject_dataset['name']}"):
            result = call_action(
                "package_show",
                {"ignore_auth": True},
                id=subject_dataset["id"],
                with_relationships=True,
            )

        assert result["related_packages"] == [object_dataset["id"]]

    def test_package_show_includes_parent_and_child_relationships_when_requested(
        self,
        test_request_context,
    ):
        subject_dataset = factories.Dataset(type="package-with-relationship")
        parent_dataset = factories.Dataset(type="package-with-relationship")
        child_dataset = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_dataset["id"],
            object_id=parent_dataset["id"],
            relation_type="child_of",
        )
        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=subject_dataset["id"],
            object_id=child_dataset["id"],
            relation_type="parent_of",
        )

        with test_request_context(f"/dataset/{subject_dataset['name']}"):
            result = call_action(
                "package_show",
                {"ignore_auth": True},
                id=subject_dataset["id"],
                with_relationships=True,
            )

        assert result["parent_packages"] == [parent_dataset["id"]]
        assert result["child_packages"] == [child_dataset["id"]]
