import pytest

from ckan.tests import factories


@pytest.fixture
def clean_db(reset_db, migrate_db_for, with_plugins):
    reset_db()
    migrate_db_for("relationship")


@pytest.fixture
def sysadmin_headers(sysadmin):
    token = factories.APIToken(user=sysadmin["name"])
    return {"Authorization": token["token"]}
