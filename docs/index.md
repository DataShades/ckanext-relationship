# Overview

`ckanext-relationship` adds relationship-backed fields to CKAN datasets and a
small API for managing those links. It integrates with `ckanext-scheming` and
can optionally expose an interactive graph UI and a sysadmin dashboard.

## Relationship types

The extension supports three relationship types:

- `related_to` creates `A related_to B` and `B related_to A`
- `child_of` creates `A child_of B` and `B parent_of A`
- `parent_of` creates `A parent_of B` and `B child_of A`

## What the extension includes

- A `related_entity` scheming preset for relationship fields.
- CKAN actions for creating, deleting, and listing relationships.
- Default form and display snippets for package, organization, and group links.
- A package autocomplete widget for large package target lists.
- An optional `relationship_graph` plugin for interactive relationship
  visualization across datasets, organizations, and groups.
- An optional `relationship_dashboard` plugin built on `ckanext-tables` for
  sysadmins.

## Entity support

| Capability | Packages | Organizations | Groups |
|---|---|---|---|
| Default relationship field | yes | yes | yes |
| Read-page links | yes | yes | yes |
| Autocomplete widget | yes | no | no |
| Graph action and graph snippet | yes | yes | yes |
| Automatic graph section | yes | yes | yes |
| Admin dashboard | yes | yes | yes |

Automatic graph placement is controlled separately for each object page type:

- datasets: `ckanext.relationship.show_relationship_graph_on_dataset_read`
- organizations: `ckanext.relationship.show_relationship_graph_on_organization_about`
- groups: `ckanext.relationship.show_relationship_graph_on_group_about`
