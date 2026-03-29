import json

import pytest

from ckan.lib.helpers import url_for
from ckan.tests import factories
from ckan.tests.helpers import call_action


def _response_text(response):
    body = response.body
    return body.decode("utf-8") if isinstance(body, bytes) else body


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestRelationshipViews:
    def test_autocomplete_excludes_current_package(self, app, sysadmin_headers):
        current = factories.Dataset(
            type="package-with-relationship",
            title="Current Project",
        )
        related = factories.Dataset(
            type="package-with-relationship",
            title="Related Project",
        )

        response = app.get(
            "/api/2/util/relationships/autocomplete"
            f"?incomplete=Project&current_entity_id={current['id']}"
            "&entity_type=package-with-relationship",
            headers=sysadmin_headers,
            status=200,
        )
        payload = json.loads(response.body)

        assert payload["ResultSet"]["Result"] == [
            {"name": related["id"], "title": "Related Project"}
        ]

    def test_autocomplete_check_sysadmin_controls_owned_only(
        self,
        app,
        sysadmin,
        sysadmin_headers,
    ):
        current = factories.Dataset(
            user=sysadmin,
            type="package-with-relationship",
            title="Current Project",
        )
        owned = factories.Dataset(
            user=sysadmin,
            type="package-with-relationship",
            title="Owned Project",
        )
        foreign = factories.Dataset(
            type="package-with-relationship",
            title="Foreign Project",
        )

        unrestricted = app.get(
            "/api/2/util/relationships/autocomplete"
            f"?incomplete=Project&current_entity_id={current['id']}"
            "&entity_type=package-with-relationship"
            "&owned_only=true&check_sysadmin=false",
            headers=sysadmin_headers,
            status=200,
        )
        restricted = app.get(
            "/api/2/util/relationships/autocomplete"
            f"?incomplete=Project&current_entity_id={current['id']}"
            "&entity_type=package-with-relationship"
            "&owned_only=true&check_sysadmin=true",
            headers=sysadmin_headers,
            status=200,
        )

        unrestricted_ids = {
            item["name"]
            for item in json.loads(unrestricted.body)["ResultSet"]["Result"]
        }
        restricted_ids = {
            item["name"] for item in json.loads(restricted.body)["ResultSet"]["Result"]
        }

        assert unrestricted_ids == {owned["id"], foreign["id"]}
        assert restricted_ids == {owned["id"]}

    def test_related_batch_returns_204_without_related_packages(self, app):
        subject = factories.Dataset(type="package-with-relationship")

        response = app.get(
            "/relationship/section"
            f"?pkg_id={subject['id']}"
            "&object_type=package-with-relationship"
            "&relation_type=related_to",
            status=204,
        )

        assert _response_text(response) == ""

    def test_related_batch_renders_first_page_and_next_batch_trigger(self, app):
        subject = factories.Dataset(type="package-with-relationship")
        alpha = factories.Dataset(
            type="package-with-relationship", title="Alpha related"
        )
        beta = factories.Dataset(type="package-with-relationship", title="Beta related")

        for related in (alpha, beta):
            call_action(
                "relationship_relation_create",
                {"ignore_auth": True},
                subject_id=subject["id"],
                object_id=related["id"],
                relation_type="related_to",
            )

        response = app.get(
            "/relationship/section"
            f"?pkg_id={subject['id']}"
            "&object_type=package-with-relationship"
            "&relation_type=related_to&size=1",
            status=200,
        )
        body = _response_text(response)

        assert "Alpha related" in body
        assert "Beta related" not in body
        assert "/relationship/section" in body
        assert "start=1" in body
        assert "size=1" in body


@pytest.mark.ckan_config(
    "ckan.plugins",
    "relationship relationship_graph scheming_datasets",
)
@pytest.mark.usefixtures("with_plugins", "clean_db", "clean_index")
class TestRelationshipGraphReadViews:
    def test_organization_about_renders_graph_snippet_by_default(self, app):
        organization = factories.Organization()
        dataset = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=dataset["id"],
            object_id=organization["id"],
            relation_type="child_of",
        )

        response = app.get(
            url_for("organization.about", id=organization["name"]),
            status=200,
        )
        body = _response_text(response)

        assert "relationship-graph-snippet" in body
        assert f'data-object-id="{organization["id"]}"' in body
        assert 'data-object-entity="organization"' in body

    def test_group_about_renders_graph_snippet_by_default(self, app):
        group = factories.Group()
        dataset = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=dataset["id"],
            object_id=group["id"],
            relation_type="related_to",
        )

        response = app.get(
            url_for("group.about", id=group["name"]),
            status=200,
        )
        body = _response_text(response)

        assert "relationship-graph-snippet" in body
        assert f'data-object-id="{group["id"]}"' in body
        assert 'data-object-entity="group"' in body

    @pytest.mark.ckan_config(
        "ckanext.relationship.show_relationship_graph_on_group_about",
        "false",
    )
    @pytest.mark.ckan_config(
        "ckanext.relationship.show_relationship_graph_on_organization_about",
        "false",
    )
    def test_about_pages_hide_graph_snippet_when_disabled(self, app):
        organization = factories.Organization()
        group = factories.Group()
        dataset = factories.Dataset(type="package-with-relationship")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=dataset["id"],
            object_id=organization["id"],
            relation_type="child_of",
        )
        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=dataset["id"],
            object_id=group["id"],
            relation_type="related_to",
        )

        organization_response = app.get(
            url_for("organization.about", id=organization["name"]),
            status=200,
        )
        group_response = app.get(
            url_for("group.about", id=group["name"]),
            status=200,
        )

        assert "relationship-graph-snippet" not in _response_text(organization_response)
        assert "relationship-graph-snippet" not in _response_text(group_response)
