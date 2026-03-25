from ckanext.relationship.utils import entity_name_by_id


class TestEntityNameById:
    def test_entity_name_by_id_when_package_exists(self, package):
        assert entity_name_by_id(package["id"]) == package["name"]

    def test_entity_name_by_id_when_organization_exists(self, organization):
        assert entity_name_by_id(organization["id"]) == organization["name"]

    def test_entity_name_by_id_when_group_exists(self, group):
        assert entity_name_by_id(group["id"]) == group["name"]

    def test_entity_name_by_id_when_no_entity_exists(self):
        assert entity_name_by_id("nonexistent") is None
