# Configuration

All configuration options are prefixed with `ckanext.relationship.`.

## `ckanext.relationship.show_relationship_graph_on_dataset_read`

Controls whether the optional relationship graph section is automatically added
to dataset read pages when the `relationship_graph` plugin is enabled.

| | |
|---|---|
| **Type** | `bool` |
| **Default** | `true` |

Default effect:

- dataset read pages render the relationship graph section automatically
- manual use of `relationship_graph/snippets/graph.html` is still available

Example:

```ini
ckanext.relationship.show_relationship_graph_on_dataset_read = false
```

---

## `ckanext.relationship.show_relationship_graph_on_group_about`

Controls whether the optional relationship graph section is automatically added
to group About pages when the `relationship_graph` plugin is enabled.

| | |
|---|---|
| **Type** | `bool` |
| **Default** | `true` |

Default effect:

- group About pages render the graph section automatically when the current
  group has at least one relationship
- manual use of `relationship_graph/snippets/graph.html` is still available

Example:

```ini
ckanext.relationship.show_relationship_graph_on_group_about = false
```

---

## `ckanext.relationship.show_relationship_graph_on_organization_about`

Controls whether the optional relationship graph section is automatically added
to organization About pages when the `relationship_graph` plugin is enabled.

| | |
|---|---|
| **Type** | `bool` |
| **Default** | `true` |

Default effect:

- organization About pages render the graph section automatically when the
  current organization has at least one relationship
- manual use of `relationship_graph/snippets/graph.html` is still available

Example:

```ini
ckanext.relationship.show_relationship_graph_on_organization_about = false
```

---

## `ckanext.relationship.views_without_relationships_in_package_show`

Controls which endpoint names omit relationship-backed fields from
`package_show` responses.

| | |
|---|---|
| **Type** | `list` |
| **Default** | `search read` |

Default effect:

- `search` responses do not include relationship fields
- `read` responses do not include relationship fields

To include relationship fields in a specific `package_show` call, pass:

```python
{"with_relationships": True}
```

Example:

```ini
ckanext.relationship.views_without_relationships_in_package_show = search read
```

---

## `ckanext.relationship.async_package_index_rebuild`

Controls how related package indexes are rebuilt after relationship changes.

When enabled, the plugin schedules background reindex jobs instead of rebuilding
indexes immediately.

| | |
|---|---|
| **Type** | `bool` |
| **Default** | `false` |

This setting affects rebuilds triggered by:

- dataset create and update when relationship-backed fields change
- dataset deletion

Direct calls to `relationship_relation_create` and
`relationship_relation_delete` do not trigger package reindexing on their own.

Example:

```ini
ckanext.relationship.async_package_index_rebuild = true
```

---

## `ckanext.relationship.redis_queue_name`

The Redis queue name used when
`ckanext.relationship.async_package_index_rebuild` is enabled.

| | |
|---|---|
| **Type** | `base` |
| **Default** | `default` |

Example:

```ini
ckanext.relationship.redis_queue_name = relationship
```

---

## `ckanext.relationship.allow_name_based_relation_create`

Controls whether new relationships may be created with entity names instead of
CKAN IDs.

| | |
|---|---|
| **Type** | `bool` |
| **Default** | `false` |

Behavior:

- `id + id` creation remains allowed
- direct calls to `relationship_relation_create` accept `name + name` only when
  this option is enabled
- mixed identifier pairs such as `id + name` are always rejected
- for scheming-backed dataset create and update, relationship fields first try to
  resolve related entity names into local CKAN IDs
- if a scheming-backed create or update still cannot resolve both sides and this
  option is enabled, it falls back to storing a temporary `name + name` pair
- when a temporary or legacy `name + name`, `id + name`, or `name + id` row
  becomes fully resolvable later, the same scheming flow canonicalizes it to
  `id + id`

This is primarily useful for syndication flows where the remote dataset keeps
the same `name` but receives a different local `id`.

Example:

```ini
ckanext.relationship.allow_name_based_relation_create = true
```

---

## Practical recommendations

- Keep the default `views_without_relationships_in_package_show` unless you
  explicitly need relationship values on search or read pages.
- Keep `show_relationship_graph_on_dataset_read = true` unless you want to
  place the graph manually in custom templates or disable it on dataset pages
  entirely.
- Keep `show_relationship_graph_on_group_about = true` unless you want to
  disable automatic graph placement on group About pages.
- Keep `show_relationship_graph_on_organization_about = true` unless you want
  to disable automatic graph placement on organization About pages.
- Turn on async index rebuilds on larger sites where synchronous reindexing
  slows down create or update requests.
- Use a dedicated queue name when you want to isolate relationship reindex jobs
  from other CKAN worker traffic.
- Leave `allow_name_based_relation_create = false` unless you need controlled
  name-based fallback for syndication or another cross-portal import flow.
