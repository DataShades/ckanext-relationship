from __future__ import annotations

import pytest

from ckan.tests import factories

from ckanext.relationship import relation_types
from ckanext.relationship.interfaces import IRelationship


class TestRelationshipTypesPlugin:
    def get_relationship_types(self) -> dict[str, str]:
        return {
            "depends_on": "required_by",
            "required_by": "depends_on",
            "references": "references",
        }

    def get_relationship_type_metadata(self) -> dict[str, dict[str, str]]:
        return {
            "depends_on": {
                "label": "Depends on",
                "color": "#7b61ff",
            },
            "required_by": {
                "label": "Required by",
                "color": "#f08c2e",
            },
            "references": {
                "label": "References",
                "color": "#2a9d8f",
            },
        }


@pytest.fixture(autouse=True)
def custom_relation_types(monkeypatch):
    original = relation_types.p.PluginImplementations

    def fake_implementations(interface):
        implementations = list(original(interface))
        if interface is IRelationship:
            return [*implementations, TestRelationshipTypesPlugin()]
        return implementations

    monkeypatch.setattr(relation_types.p, "PluginImplementations", fake_implementations)


@pytest.fixture
def clean_db(reset_db, migrate_db_for, with_plugins):
    reset_db()
    migrate_db_for("relationship")


@pytest.fixture
def sysadmin_headers(sysadmin):
    token = factories.APIToken(user=sysadmin["name"])
    return {"Authorization": token["token"]}
