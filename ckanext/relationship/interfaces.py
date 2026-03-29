from __future__ import annotations

from ckan.plugins.interfaces import Interface


class IRelationship(Interface):
    """Allow extensions to register additional relationship types."""

    def get_relationship_types(self) -> dict[str, str]:
        """Return a mapping of relation_type -> reverse_relation_type.

        Symmetric relation types should map to themselves.
        Asymmetric relation types must provide both sides, for example:
        {"depends_on": "required_by", "required_by": "depends_on"}.
        """
        return {}

    def get_relationship_type_metadata(self) -> dict[str, dict[str, str]]:
        """Return optional UI metadata keyed by relation type.

        Supported keys:

        - `label`: human-friendly label for graph legends and UI
        - `color`: CSS color used for graph edges and legend markers
        """
        return {}
