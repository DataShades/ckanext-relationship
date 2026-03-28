# Helpers and Templates

`ckanext-relationship` exposes helper functions and Jinja snippets for form
widgets and read-page rendering.

## Template helpers

The plugin registers the following helpers:

### `relationship_get_entity_list(entity, entity_type, entity_query=None, include_private=True)`

Returns the available target entities for a relationship field.

Use this helper when you want to build a custom widget with the same target list
logic as the default field.

### `relationship_get_current_relations_list(field, data)`

Returns the currently selected related IDs for a field.

Use it to pre-populate a custom form or display snippet.

### `relationship_get_selected_json(selected_ids=None)`

Returns the JSON payload used to pre-populate the autocomplete widget.

This helper is intended for package autocomplete fields.

### `relationship_get_choices_for_related_entity_field(field, current_entity_id)`

Builds the `(value, label)` pairs for the default select widget.

Use it when you want the same option list as the default relationship widget.

### `relationship_format_autocomplete(packages)`

Formats autocomplete results into CKAN’s expected completion JSON shape.

You can replace it by passing another helper name with
`format_autocomplete_helper`.

The following graph helpers are registered only when the optional
`relationship_graph` plugin is enabled.

### `relationship_has_relations(pkg_type)`

Returns `True` when the given dataset type has relationship-backed scheming
fields.

### `relationship_get_relation_types(pkg_type)`

Returns the distinct relationship types configured for the given dataset type.

### `relationship_show_graph_on_read()`

Returns whether the graph section should be added automatically to dataset read
pages.

## Scheming snippets

### `scheming/form_snippets/related_entity.html`

Default select-based widget for the `related_entity` preset.

Use it when:

- you need package, organization, or group relations
- the option list is reasonably small
- you want a standard select control

### `scheming/form_snippets/related_entity_with_autocomplete.html`

Alternative package-only autocomplete widget.

Use it when:

- the related package list is large
- preloading up to 1000 choices is not practical

See [Package autocomplete](schema/index.md#package-autocomplete) for the full
details.

### `scheming/display_snippets/related_entity.html`

Read-only rendering for relationship-backed fields.

It renders related entities as links to their CKAN pages.

## Lazy related-package snippets

The extension also ships snippets for progressively loading long related-package
lists.

### `snippets/relationship_related_packages_list.html`

Use this as the outer snippet for a related-package list.

Example:

```jinja
{% snippet 'snippets/relationship_related_packages_list.html',
    pkg_id=pkg.id,
    object_type='package-with-relationship',
    relation_type='related_to',
    page_size=20 %}
```

### `snippets/relationship_related_batch.html`

This is the follow-up snippet used by `/relationship/section`.

### `snippets/relationship_spinner.html`

Simple loading indicator used by the package list snippets.

## Graph snippet

The reusable graph snippet is `relationship_graph/snippets/graph.html`.

For full usage, controls, rendering behavior, and screenshots, see
[Graph](graph.md).

## When to use which rendering approach

| Need | Recommended piece |
|---|---|
| Simple schema-backed select widget | `related_entity.html` |
| Large package relationship field | `related_entity_with_autocomplete.html` |
| Simple read-page list of links | `display_snippets/related_entity.html` |
| Infinite-scroll related package cards/list | `relationship_related_packages_list.html` + `/relationship/section` |

## Practical caveats

- The autocomplete helpers and endpoint are package-only.
- The HTMX route and batch snippets are package-only.
- The graph snippet, graph helpers, and `/api/2/util/relationships/graph`
  route require the optional `relationship_graph` plugin.
