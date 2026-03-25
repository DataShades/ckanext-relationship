# Installation

## Requirements

`ckanext-relationship` is intended for CKAN sites that already use
`ckanext-scheming`.

The extension targets CKAN 2.10 and newer.

## Runtime installation

Install the base extension in your CKAN virtual environment:

```sh
pip install ckanext-relationship
```

If you also want the admin dashboard, install the optional dashboard extra:

```sh
pip install "ckanext-relationship[dashboard]"
```

## Source installation

```sh
git clone https://github.com/DataShades/ckanext-relationship.git
cd ckanext-relationship
pip install -e .
```

For the optional dashboard:

```sh
pip install -e ".[dashboard]"
```

## Enable CKAN plugins

For the base relationship features, enable `scheming_datasets` and
`relationship`:

```ini
ckan.plugins = ... scheming_datasets relationship ...
```

For the optional dashboard, also enable `tables` and
`relationship_dashboard`:

```ini
ckan.plugins = ... scheming_datasets tables relationship relationship_dashboard ...
```

## Run the database migration

Run the extension migration after installation:

```sh
ckan -c /etc/ckan/default/ckan.ini db upgrade -p relationship
```

## Restart CKAN

Restart CKAN after changing plugins or running migrations. For example, on a
typical Ubuntu/Apache deployment:

```sh
sudo service apache2 reload
```

## Developer installation

To work on the extension locally:

```sh
git clone https://github.com/DataShades/ckanext-relationship.git
cd ckanext-relationship
pip install -e ".[docs]"
pip install -r dev-requirements.txt
```

If you are also working on the dashboard:

```sh
pip install -e ".[dashboard,docs]"
```

## Building the documentation

Serve the docs locally:

```sh
mkdocs serve
```

Build the static site:

```sh
mkdocs build
```

## Running tests

Run the test suite from the repository root:

```sh
pytest --ckan-ini=test.ini
```
