# Configuration

All configuration options are prefixed with `ckanext.relationship.`.

## `ckanext.relationship.show_relationship_graph_on_read`

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
ckanext.relationship.show_relationship_graph_on_read = false
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

## Practical recommendations

- Keep the default `views_without_relationships_in_package_show` unless you
  explicitly need relationship values on search or read pages.
- Keep `show_relationship_graph_on_read = true` unless you want to place the
  graph manually in custom templates or disable it on read pages entirely.
- Turn on async index rebuilds on larger sites where synchronous reindexing
  slows down create or update requests.
- Use a dedicated queue name when you want to isolate relationship reindex jobs
  from other CKAN worker traffic.
