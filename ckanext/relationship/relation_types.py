from __future__ import annotations

from ckan import plugins as p

from ckanext.relationship.interfaces import IRelationship

DEFAULT_RELATION_TYPE_REVERSE_MAP: dict[str, str] = {
    "related_to": "related_to",
    "child_of": "parent_of",
    "parent_of": "child_of",
}


class RelationTypeConfigurationError(ValueError):
    @classmethod
    def conflicting_mapping(
        cls,
        relation_type: str,
        existing: str,
        reverse_relation_type: str,
    ) -> RelationTypeConfigurationError:
        return cls(
            "Conflicting reverse relation mapping for "
            f"{relation_type}: {existing} != {reverse_relation_type}"
        )

    @classmethod
    def empty_relation_type(cls) -> RelationTypeConfigurationError:
        return cls("Relation types must be non-empty strings")

    @classmethod
    def non_reciprocal_mapping(
        cls,
        relation_type: str,
        reverse_relation_type: str,
        reverse_of_reverse: str | None,
    ) -> RelationTypeConfigurationError:
        return cls(
            "Relation type mappings must be reciprocal: "
            f"{relation_type} -> {reverse_relation_type}, "
            f"but {reverse_relation_type} -> {reverse_of_reverse!r}"
        )

    @classmethod
    def unknown_relation_type(
        cls,
        relation_type: str,
    ) -> RelationTypeConfigurationError:
        return cls(
            "Relationship type metadata references an unknown relation type: "
            f"{relation_type}"
        )

    @classmethod
    def unsupported_metadata_key(
        cls,
        relation_type: str,
        key: str,
    ) -> RelationTypeConfigurationError:
        return cls(
            "Unsupported relationship type metadata key "
            f"{key!r} for relation type {relation_type!r}"
        )

    @classmethod
    def empty_metadata_value(
        cls,
        relation_type: str,
        key: str,
    ) -> RelationTypeConfigurationError:
        return cls(
            "Relationship type metadata values must be non-empty strings: "
            f"{relation_type}.{key}"
        )


def get_relation_type_reverse_map() -> dict[str, str]:
    reverse_map = DEFAULT_RELATION_TYPE_REVERSE_MAP.copy()

    for plugin in p.PluginImplementations(IRelationship):
        provided = getattr(plugin, "get_relationship_types", dict)() or {}

        for relation_type, reverse_relation_type in provided.items():
            existing = reverse_map.get(relation_type)
            if existing is not None and existing != reverse_relation_type:
                raise RelationTypeConfigurationError.conflicting_mapping(
                    relation_type,
                    existing,
                    reverse_relation_type,
                )
            reverse_map[relation_type] = reverse_relation_type

    _validate_relation_type_reverse_map(reverse_map)
    return reverse_map


def get_relation_types() -> list[str]:
    return list(get_relation_type_reverse_map())


def get_relation_type_metadata() -> dict[str, dict[str, str]]:
    reverse_map = get_relation_type_reverse_map()
    metadata: dict[str, dict[str, str]] = {}

    for plugin in p.PluginImplementations(IRelationship):
        provided = getattr(plugin, "get_relationship_type_metadata", dict)() or {}

        for relation_type, definition in provided.items():
            if relation_type not in reverse_map:
                raise RelationTypeConfigurationError.unknown_relation_type(
                    relation_type
                )

            existing = metadata.setdefault(relation_type, {})
            for key, value in definition.items():
                if key not in {"label", "color"}:
                    raise RelationTypeConfigurationError.unsupported_metadata_key(
                        relation_type,
                        key,
                    )
                if not value:
                    raise RelationTypeConfigurationError.empty_metadata_value(
                        relation_type,
                        key,
                    )
                existing[key] = value

    return metadata


def get_reverse_relation_type(relation_type: str) -> str:
    return get_relation_type_reverse_map()[relation_type]


def is_supported_relation_type(relation_type: str) -> bool:
    return relation_type in get_relation_type_reverse_map()


def is_symmetric_relation_type(relation_type: str) -> bool:
    return get_reverse_relation_type(relation_type) == relation_type


def _validate_relation_type_reverse_map(reverse_map: dict[str, str]) -> None:
    for relation_type, reverse_relation_type in reverse_map.items():
        if not relation_type or not reverse_relation_type:
            raise RelationTypeConfigurationError.empty_relation_type()

        reverse_of_reverse = reverse_map.get(reverse_relation_type)
        if reverse_of_reverse != relation_type:
            raise RelationTypeConfigurationError.non_reciprocal_mapping(
                relation_type,
                reverse_relation_type,
                reverse_of_reverse,
            )
