# Actions and API

This page documents the relationship action API, the public routes registered by
the extension, and its `package_show` integration.

## Core actions

### `relationship_relation_create`

Creates a relationship.

Parameters:

| Key | Required | Notes |
|---|---|---|
| `subject_id` | yes | Use the CKAN ID. Entity names are also accepted in the current implementation |
| `object_id` | yes | Use the CKAN ID. Entity names are also accepted in the current implementation |
| `relation_type` | yes | `related_to`, `child_of`, or `parent_of` |
| `extras` | no | Extra metadata stored with the relationship |

Behavior:

- Duplicate relationships are ignored.
- The reverse relationship is created automatically.

Example:

```python
tk.get_action("relationship_relation_create")(
    {"user": "alice"},
    {
        "subject_id": package_a_id,
        "object_id": package_b_id,
        "relation_type": "related_to",
        "extras": {"source": "manual-link"},
    },
)
```

### `relationship_relation_delete`

Deletes a relationship.

Parameters:

| Key | Required | Notes |
|---|---|---|
| `subject_id` | yes | CKAN ID or entity name |
| `object_id` | yes | CKAN ID or entity name |
| `relation_type` | no | If omitted, all matching rows between the two entities are removed |

Behavior:

- Removes the relationship in both directions.

### `relationship_relations_list`

Returns matching relationship rows for a subject.

Parameters:

| Key | Required | Notes |
|---|---|---|
| `subject_id` | yes | Use the subject entity ID. Name lookups are supported only for some legacy rows |
| `object_entity` | no | `package`, `organization`, or `group` |
| `object_type` | no | Related entity type |
| `relation_type` | no | `related_to`, `child_of`, or `parent_of` |

### `relationship_relations_ids_list`

Same filter contract as `relationship_relations_list`, but returns a unique list
of `object_id` values.

### Identifier behavior

For predictable results, use CKAN IDs in all relationship actions.

The current implementation also supports some name-based behavior for backward
compatibility:

- `relationship_relation_create` accepts entity names as well as IDs
- `relationship_relation_delete` can remove rows addressed by ID or by name
- `relationship_relations_list` and `relationship_relations_ids_list` are
  asymmetric: an ID lookup can find rows created by name, but a name lookup
  does not reliably find rows created by ID

### `relationship_get_entity_list`

Returns entities of a given kind and type.

Parameters:

| Key | Required |
|---|---|
| `entity` | yes |
| `entity_type` | yes |

Return shape:

- list of `(id, name, title)` tuples

### `relationship_autocomplete`

Package-only autocomplete backend used by the autocomplete form snippet.

Parameters:

| Key | Required |
|---|---|
| `current_entity_id` | yes |
| `entity_type` | yes |
| `incomplete` | no |
| `updatable_only` | no |
| `owned_only` | no |
| `check_sysadmin` | no |
| `format_autocomplete_helper` | no |

Return shape:

- JSON payload formatted by `relationship_format_autocomplete` or a custom
  helper

See [Package autocomplete](schema/index.md#package-autocomplete) for
field-level usage.

## Public routes

### `/api/2/util/relationships/autocomplete`

Purpose:

- Frontend endpoint for the package autocomplete widget.
- Useful for custom frontends that want the same search behavior.

### `/relationship/section`

Purpose:

- Fragment endpoint for lazy-loading related packages with the shipped template
  snippets.

Query parameters:

| Parameter | Required |
|---|---|
| `pkg_id` | yes |
| `object_type` | yes |
| `relation_type` | yes |
| `start` | no |
| `size` | no |

Notes:

- This route is package-only.
- The default batch size is `20`.

## `package_show` chaining

Relationship-backed fields can be included in `package_show` output as lists of
related entity IDs.

Example:

```python
package = tk.get_action("package_show")(
    {"ignore_auth": True},
    {"id": package_id, "with_relationships": True},
)

related_ids = package["related_packages"]
```

### Default hiding on `search` and `read`

By default, relationship fields are omitted from `package_show` output on:

- `search`
- `read`

You can:

- Change that globally with
  `ckanext.relationship.views_without_relationships_in_package_show`.
- Force inclusion for a specific request by passing `with_relationships=True`.
