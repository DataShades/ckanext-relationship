import json

import pytest

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
