from __future__ import annotations

from ckan.logic.schema import validator_args
from ckan.types import Schema, Validator, ValidatorFactory


@validator_args
def graph(  # noqa: PLR0913
    not_empty: Validator,
    one_of: ValidatorFactory,
    default: ValidatorFactory,
    ignore_missing: Validator,
    is_positive_integer: Validator,
    boolean_validator: Validator,
    json_list_or_string: Validator,
    list_of_strings: Validator,
) -> Schema:
    return {
        "object_id": [
            not_empty,
        ],
        "object_entity": [
            default("package"),
            one_of(["package", "organization", "group"]),
        ],
        "object_type": [
            default("dataset"),
        ],
        "depth": [
            default(1),
            is_positive_integer,
        ],
        "relation_types": [
            ignore_missing,
            json_list_or_string,
            list_of_strings,
        ],
        "max_nodes": [
            default(100),
            is_positive_integer,
        ],
        "include_unresolved": [
            default(True),
            boolean_validator,
        ],
        "include_reverse": [
            default(True),
            boolean_validator,
        ],
        "with_titles": [
            default(True),
            boolean_validator,
        ],
    }
