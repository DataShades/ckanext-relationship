import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests import factories
from ckan.tests.helpers import call_action

from ckanext.relationship.model.relationship import Relationship


def _exact_relation(subject_id: str, object_id: str, relation_type: str):
    return (
        model.Session.query(Relationship)
        .filter_by(
            subject_id=subject_id,
            object_id=object_id,
            relation_type=relation_type,
        )
        .one_or_none()
    )


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


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestPackageRelationshipIdentifierModes:
    def test_package_create_resolves_related_name_to_local_id(self):
        organization = factories.Organization()
        related = factories.Dataset(type="package-with-relationship")

        subject = call_action(
            "package_create",
            {"ignore_auth": True},
            name="syndicated-subject",
            title="Syndicated subject",
            type="package-with-relationship",
            owner_org=organization["id"],
            related_packages=[related["name"]],
        )

        relation = Relationship.by_object_id(
            subject["id"],
            related["id"],
            "related_to",
        )

        assert relation is not None
        assert relation.subject_id == subject["id"]
        assert relation.object_id == related["id"]

    def test_package_create_rejects_new_name_based_relation_by_default(self):
        organization = factories.Organization()

        with pytest.raises(tk.ValidationError):
            call_action(
                "package_create",
                {"ignore_auth": True},
                name="syndicated-subject",
                title="Syndicated subject",
                type="package-with-relationship",
                owner_org=organization["id"],
                related_packages=["remote-related-name"],
            )

    @pytest.mark.ckan_config(
        "ckanext.relationship.allow_name_based_relation_create", True
    )
    def test_package_create_stores_name_pair_when_remote_target_is_missing(self):
        organization = factories.Organization()

        subject = call_action(
            "package_create",
            {"ignore_auth": True},
            name="syndicated-subject",
            title="Syndicated subject",
            type="package-with-relationship",
            owner_org=organization["id"],
            related_packages=["remote-related-name"],
        )

        relation = Relationship.by_object_id(
            subject["id"],
            "remote-related-name",
            "related_to",
        )

        assert relation is not None
        assert relation.subject_id == subject["name"]
        assert relation.object_id == "remote-related-name"

    @pytest.mark.ckan_config(
        "ckanext.relationship.allow_name_based_relation_create", True
    )
    def test_package_create_canonicalizes_name_relations_when_target_arrives(self):
        organization = factories.Organization()

        subject = call_action(
            "package_create",
            {"ignore_auth": True},
            name="syndicated-subject",
            title="Syndicated subject",
            type="package-with-relationship",
            owner_org=organization["id"],
            related_packages=["remote-related-name"],
        )

        assert _exact_relation(subject["name"], "remote-related-name", "related_to")
        assert _exact_relation("remote-related-name", subject["name"], "related_to")

        target = call_action(
            "package_create",
            {"ignore_auth": True},
            name="remote-related-name",
            title="Remote related",
            type="package-with-relationship",
            owner_org=organization["id"],
        )

        assert _exact_relation(subject["id"], target["id"], "related_to")
        assert _exact_relation(target["id"], subject["id"], "related_to")
        assert _exact_relation(subject["name"], target["name"], "related_to") is None
        assert _exact_relation(target["name"], subject["name"], "related_to") is None

    def test_package_update_canonicalizes_legacy_id_name_relation_pair(self):
        subject = factories.Dataset(type="package-with-relationship")
        target = factories.Dataset(type="package-with-relationship")

        model.Session.add(
            Relationship(
                subject_id=subject["id"],
                object_id=target["name"],
                relation_type="related_to",
            )
        )
        model.Session.add(
            Relationship(
                subject_id=target["name"],
                object_id=subject["id"],
                relation_type="related_to",
            )
        )
        model.Session.commit()

        call_action(
            "package_patch",
            {"ignore_auth": True},
            id=subject["id"],
            title="Updated subject",
        )

        assert _exact_relation(subject["id"], target["id"], "related_to")
        assert _exact_relation(target["id"], subject["id"], "related_to")
        assert _exact_relation(subject["id"], target["name"], "related_to") is None
        assert _exact_relation(target["name"], subject["id"], "related_to") is None

    def test_package_update_canonicalizes_legacy_name_id_relation_pair(self):
        subject = factories.Dataset(type="package-with-relationship")
        target = factories.Dataset(type="package-with-relationship")

        model.Session.add(
            Relationship(
                subject_id=subject["name"],
                object_id=target["id"],
                relation_type="related_to",
            )
        )
        model.Session.add(
            Relationship(
                subject_id=target["id"],
                object_id=subject["name"],
                relation_type="related_to",
            )
        )
        model.Session.commit()

        call_action(
            "package_patch",
            {"ignore_auth": True},
            id=subject["id"],
            title="Updated subject",
        )

        assert _exact_relation(subject["id"], target["id"], "related_to")
        assert _exact_relation(target["id"], subject["id"], "related_to")
        assert _exact_relation(subject["name"], target["id"], "related_to") is None
        assert _exact_relation(target["id"], subject["name"], "related_to") is None
