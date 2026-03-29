from __future__ import annotations

from ckan.logic.schema import validator_args
from ckan.types import Schema, Validator, ValidatorFactory

from ckanext.relationship import relation_types


@validator_args
def relation_create(
    not_empty: Validator,
    one_of: ValidatorFactory,
    default: ValidatorFactory,
    convert_to_json_if_string: Validator,
    dict_only: Validator,
) -> Schema:
    return {
        "subject_id": [
            not_empty,
        ],
        "object_id": [
            not_empty,
        ],
        "relation_type": [
            one_of(relation_types.get_relation_types()),
        ],
        "extras": [default("{}"), convert_to_json_if_string, dict_only],
    }


@validator_args
def relation_delete(
    not_empty: Validator, one_of: ValidatorFactory, ignore_missing: Validator
) -> Schema:
    return {
        "subject_id": [
            not_empty,
        ],
        "object_id": [
            not_empty,
        ],
        "relation_type": [
            ignore_missing,
            one_of(relation_types.get_relation_types()),
        ],
    }


@validator_args
def relations_list(
    not_empty: Validator, one_of: ValidatorFactory, ignore_missing: Validator
) -> Schema:
    return {
        "subject_id": [
            not_empty,
        ],
        "object_entity": [
            ignore_missing,
            one_of(["package", "organization", "group"]),
        ],
        "object_type": [
            ignore_missing,
        ],
        "relation_type": [
            ignore_missing,
            one_of(relation_types.get_relation_types()),
        ],
    }


@validator_args
def relations_ids_list(
    not_empty: Validator, one_of: ValidatorFactory, ignore_missing: Validator
) -> Schema:
    return {
        "subject_id": [
            not_empty,
        ],
        "object_entity": [
            ignore_missing,
            one_of(["package", "organization", "group"]),
        ],
        "object_type": [
            ignore_missing,
        ],
        "relation_type": [
            ignore_missing,
            one_of(relation_types.get_relation_types()),
        ],
    }


@validator_args
def get_entity_list(not_empty: Validator, one_of: ValidatorFactory) -> Schema:
    return {
        "entity": [
            not_empty,
            one_of(["package", "organization", "group"]),
        ],
        "entity_type": [
            not_empty,
        ],
    }


@validator_args
def autocomplete(not_empty: Validator) -> Schema:
    return {
        "incomplete": [],
        "current_entity_id": [
            not_empty,
        ],
        "entity_type": [
            not_empty,
        ],
        "updatable_only": [],
        "owned_only": [],
        "check_sysadmin": [],
        "format_autocomplete_helper": [],
    }
