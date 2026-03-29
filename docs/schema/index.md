# Scheming Fields

Use the `related_entity` preset to add relationship-backed fields to a scheming
dataset type.

## Minimal field example

```yaml
- field_name: related_packages
  preset: related_entity
  label: Related packages
  related_entity: package
  related_entity_type: package-with-relationship
  relation_type: related_to
  multiple: true
```

Besides normal scheming keys such as `field_name`, `label`, and `preset`, the
relationship field uses a mix of:

- relationship-specific keys introduced by this extension
- general scheming field keys that still apply to this preset
- widget-specific keys used by the shipped form snippets

## Required relationship options

| Key | Meaning |
|---|---|
| `related_entity` | Target kind: `package`, `organization`, or `group` |
| `related_entity_type` | The type of the related entity |
| `relation_type` | One of the configured relationship types |

## Optional relationship keys

These keys are introduced by `ckanext-relationship` itself.

| Key | Meaning |
|---|---|
| `updatable_only` | Show only entities the current user can update |
| `owned_only` | For package targets, show only packages owned by the current user |
| `related_entity_query` | Custom query or filter for the available choices |

## General scheming field keys

These keys come from `ckanext-scheming`, not from this extension. They still
apply because `related_entity` is a normal scheming field preset.

| Key | Meaning |
|---|---|
| `required` | Require at least one related entity |
| `multiple` | Allow selecting more than one related entity |
| `form_snippet` | Override the form widget |
| `display_snippet` | Override the read-only widget |
| `form_placeholder` | Placeholder text used by the active form widget |
| `form_attrs` | Extra HTML attributes for the active form widget |

## Default select widget options

These keys are read by the shipped select-based relationship widget.

| Key | Meaning |
|---|---|
| `select_size` | Size of the default select widget |
| `hidden_from_form` | Hide the default form control |
| `form_select_attrs` | Extra HTML attributes for the default select widget |

## Package autocomplete options

These keys are only relevant when `form_snippet` is set to
`related_entity_with_autocomplete.html`.

| Key | Meaning |
|---|---|
| `check_sysadmin` | Apply `owned_only` to sysadmins in autocomplete mode |
| `format_autocomplete_helper` | Custom formatter for autocomplete responses |

## Relation types

| `relation_type` | Meaning |
|---|---|
| `related_to` | Symmetric relationship |
| `child_of` | The current entity is the child |
| `parent_of` | The current entity is the parent |

These are the built-in types. Other extensions can register additional types by
implementing `ckanext.relationship.interfaces.IRelationship`.

## Target entities

`related_entity` can point to:

- `package`
- `organization`
- `group`

Examples:

- package -> package type `project`
- package -> organization type `organization`
- group -> group type `group`

## Default widget behavior

The preset uses a select-based widget by default.

- It works for package, organization, and group relations.
- Existing relations are shown as selected values.
- The current entity is not offered as a target.
- If `multiple` is false and the field is not required, the widget includes a
  `No relation` option.

## Identifier behavior in scheming fields

The shipped relationship widgets submit entity IDs.

If a custom importer or syndication flow injects entity names into a
scheming-backed relationship field instead:

- the validator first tries to resolve those names to local CKAN IDs
- if both sides can be resolved, the stored relationship is canonical `id + id`
- if a target still does not exist locally and
  `ckanext.relationship.allow_name_based_relation_create = true`, the create or
  update falls back to a temporary `name + name` row
- once both local entities exist, later scheming-backed create or update calls
  rewrite that temporary or legacy `name + name`, `id + name`, or `name + id`
  row to canonical `id + id`

## Display behavior

The default display snippet renders related entities as links to their CKAN
pages.

!!! tip "When to switch to autocomplete"

    Use the package autocomplete widget when a package relationship field has
    too many possible targets for a regular select widget.

## Package autocomplete

Use `scheming/form_snippets/related_entity_with_autocomplete.html` when a
package relationship field has too many possible targets for the default select
widget.

The autocomplete widget is package-only. Do not use it for organization or
group relations.

If this snippet is configured on a non-package relationship field, the
extension falls back to the default select widget instead of using the
package-only autocomplete endpoint.

### Example field

```yaml
- field_name: related_projects
  preset: related_entity
  form_snippet: related_entity_with_autocomplete.html
  label: Related projects
  related_entity: package
  related_entity_type: project
  relation_type: related_to
  multiple: true
  owned_only: false
  updatable_only: true
  form_placeholder: Start typing a project title
```

### Useful field options

| Key | Meaning |
|---|---|
| `form_placeholder` | Placeholder text shown before the user starts typing |
| `owned_only` | Limit choices to the current user's packages |
| `updatable_only` | Limit choices to packages the current user can update |
| `check_sysadmin` | Apply `owned_only` to sysadmins as well |
| `format_autocomplete_helper` | Custom formatter for the JSON response |

### Autocomplete behavior

- Selected values are stored as package IDs.
- Results are limited to the requested package type.
- The current package is excluded from the suggestions.
- `owned_only` and `updatable_only` can be combined.

### `owned_only` and `check_sysadmin`

`owned_only` filters packages by `creator_user_id`.

For sysadmins, the default behavior is:

- `owned_only=true`, `check_sysadmin=false` -> sysadmin sees all packages
- `owned_only=true`, `check_sysadmin=true` -> sysadmin is filtered the same way
  as a normal user

### Public endpoint

The widget uses this endpoint:

```text
/api/2/util/relationships/autocomplete
```

If you are building a custom frontend against this endpoint, the supported query
parameters are:

| Parameter | Meaning |
|---|---|
| `incomplete` | Search string typed by the user |
| `current_entity_id` | Current package ID, excluded from results |
| `entity` | Must be `package` |
| `entity_type` | Package type to search |
| `updatable_only` | If true, keep only packages the current user can update |
| `owned_only` | If true, keep only packages created by the current user |
| `check_sysadmin` | If true, apply `owned_only` even for sysadmins |
| `format_autocomplete_helper` | Helper name used to format the JSON payload |

### When to use autocomplete

Use autocomplete when:

- the related package type is large
- loading the full package choice list is too slow
- you want incremental search instead of a large select widget

Stay with the default select when:

- the target list is small
- you need organization or group relations
- you want the full option list visible immediately
