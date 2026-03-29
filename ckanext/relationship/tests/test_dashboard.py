import json

import pytest

import ckan.tests.factories as factories
from ckan.lib.helpers import url_for
from ckan.tests.helpers import call_action

from ckanext.relationship_dashboard.table import RelationshipDashboardTable


@pytest.mark.ckan_config(
    "ckan.plugins",
    "scheming_datasets relationship tables relationship_dashboard",
)
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRelationshipDashboard:
    def test_dashboard_requires_sysadmin(self, app, sysadmin_headers):
        url = url_for("relationship_dashboard.dashboard")

        app.get(url, status=403)
        response = app.get(
            url,
            headers={
                **sysadmin_headers,
                "X-Requested-With": "XMLHttpRequest",
            },
            status=200,
        )

        assert '"data"' in response

    def test_dashboard_button_visible_for_sysadmin(self, app, sysadmin_headers):
        response = app.get("/", headers=sysadmin_headers, status=200)

        assert url_for("relationship_dashboard.dashboard") in response

    def test_dashboard_ajax_deduplicates_reverse_rows(self, app, sysadmin_headers):
        parent = factories.Dataset(type="package-with-relationship", title="Parent")
        child = factories.Dataset(type="package-with-relationship", title="Child")

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=child["id"],
            object_id=parent["id"],
            relation_type="child_of",
            extras={"source": "test-suite"},
        )

        response = app.get(
            url_for("relationship_dashboard.dashboard"),
            headers={
                **sysadmin_headers,
                "X-Requested-With": "XMLHttpRequest",
            },
            status=200,
        )
        payload = json.loads(response.body)

        assert payload["total"] == 1
        assert f"/dataset/{parent['id']}" in payload["data"][0]["subject_label"]
        assert ">Parent</a>" in payload["data"][0]["subject_label"]
        assert f"/dataset/{child['id']}" in payload["data"][0]["object_label"]
        assert ">Child</a>" in payload["data"][0]["object_label"]
        assert payload["data"][0]["subject_kind"] == "package"
        assert payload["data"][0]["object_kind"] == "package"
        assert payload["data"][0]["relation_type"] == "parent_of"
        assert "test-suite" in payload["data"][0]["extras"]

    def test_dashboard_ajax_deduplicates_plugin_asymmetric_rows(
        self, app, sysadmin_headers
    ):
        dependency = factories.Dataset(
            type="package-with-relationship", title="Dependency"
        )
        dependent = factories.Dataset(
            type="package-with-relationship", title="Dependent"
        )

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=dependent["id"],
            object_id=dependency["id"],
            relation_type="depends_on",
        )

        response = app.get(
            url_for("relationship_dashboard.dashboard"),
            headers={
                **sysadmin_headers,
                "X-Requested-With": "XMLHttpRequest",
            },
            status=200,
        )
        payload = json.loads(response.body)

        assert payload["total"] == 1
        assert f"/dataset/{dependency['id']}" in payload["data"][0]["subject_label"]
        assert ">Dependency</a>" in payload["data"][0]["subject_label"]
        assert f"/dataset/{dependent['id']}" in payload["data"][0]["object_label"]
        assert ">Dependent</a>" in payload["data"][0]["object_label"]
        assert payload["data"][0]["relation_type"] == "required_by"

    def test_dashboard_ajax_deduplicates_plugin_symmetric_rows(
        self, app, sysadmin_headers
    ):
        alpha = factories.Dataset(type="package-with-relationship", title="Alpha")
        beta = factories.Dataset(type="package-with-relationship", title="Beta")
        subject, object_ = sorted(
            [(alpha["id"], "Alpha"), (beta["id"], "Beta")],
            key=lambda item: item[0],
        )

        call_action(
            "relationship_relation_create",
            {"ignore_auth": True},
            subject_id=alpha["id"],
            object_id=beta["id"],
            relation_type="references",
        )

        response = app.get(
            url_for("relationship_dashboard.dashboard"),
            headers={
                **sysadmin_headers,
                "X-Requested-With": "XMLHttpRequest",
            },
            status=200,
        )
        payload = json.loads(response.body)

        assert payload["total"] == 1
        assert f"/dataset/{subject[0]}" in payload["data"][0]["subject_label"]
        assert f">{subject[1]}</a>" in payload["data"][0]["subject_label"]
        assert f"/dataset/{object_[0]}" in payload["data"][0]["object_label"]
        assert f">{object_[1]}</a>" in payload["data"][0]["object_label"]
        assert payload["data"][0]["relation_type"] == "references"

    def test_dashboard_query_uses_joins_for_entity_metadata(self):
        stmt = RelationshipDashboardTable().data_source.stmt
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).upper()

        assert sql.count("LEFT OUTER JOIN") >= 4
        assert "SUBJECT_PACKAGE" in sql
        assert "OBJECT_PACKAGE" in sql
        assert "REQUIRED_BY" in sql
        assert "REFERENCES" in sql
        assert "LIMIT 1" not in sql
