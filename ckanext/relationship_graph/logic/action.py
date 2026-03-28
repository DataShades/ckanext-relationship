from __future__ import annotations

from collections import deque
from typing import Any, NamedTuple

import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan import logic, model
from ckan.logic import validate
from ckan.types import Context

from ckanext.relationship.model.relationship import Relationship
from ckanext.relationship_graph.logic import schema

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized

ENTITY_ROUTE_MAP = {
    "group": "group.read",
    "organization": "organization.read",
    "package": "dataset.read",
}
ENTITY_SHOW_ACTION_MAP = {
    "group": "group_show",
    "organization": "organization_show",
    "package": "package_show",
}
GRAPH_MAX_DEPTH = 4
GRAPH_MAX_NODES = 300


class GraphNodeResolution(NamedTuple):
    node: dict[str, Any]
    lookup_ids: set[str]


def get_actions():
    return {
        "relationship_graph": relationship_graph,
    }


@tk.side_effect_free
@validate(schema.graph)
def relationship_graph(  # noqa: C901, PLR0912, PLR0915
    context: Context, data_dict: dict[str, Any]
) -> dict[str, Any]:
    tk.check_access("relationship_graph", context, data_dict)

    depth = data_dict["depth"]
    max_nodes = data_dict["max_nodes"]
    relation_types = _validate_graph_data(data_dict)
    include_unresolved = data_dict["include_unresolved"]
    include_reverse = data_dict["include_reverse"]
    with_titles = data_dict["with_titles"]
    object_entity = data_dict["object_entity"]
    object_type = data_dict["object_type"]

    center_resolution = _resolve_graph_node(
        context,
        data_dict["object_id"],
        preferred_entity=object_entity,
        preferred_type=object_type,
        fallback_entity=object_entity,
        fallback_type=object_type,
        include_unresolved=False,
        with_titles=with_titles,
        strict=True,
    )

    nodes_by_id: dict[str, dict[str, Any]] = {}
    lookup_ids_by_node: dict[str, set[str]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    visited: set[str] = set()
    queue: deque[str] = deque()

    center_id = center_resolution.node["id"]
    _upsert_graph_node(
        nodes_by_id,
        lookup_ids_by_node,
        center_resolution,
        level=0,
        is_center=True,
        max_nodes=max_nodes,
    )
    queue.append(center_id)

    truncated = False

    while queue:
        current_node_id = queue.popleft()

        if current_node_id in visited:
            continue

        visited.add(current_node_id)
        current_node = nodes_by_id[current_node_id]
        current_level = current_node["level"]

        if current_level >= depth:
            continue

        current_lookup_ids = lookup_ids_by_node[current_node_id]

        for relation in _get_graph_relationships(
            context["session"],
            current_lookup_ids,
            relation_types,
            include_reverse,
        ):
            source_resolution = _resolve_graph_node(
                context,
                relation.subject_id,
                fallback_entity=object_entity,
                fallback_type=object_type,
                include_unresolved=include_unresolved,
                with_titles=with_titles,
            )
            target_resolution = _resolve_graph_node(
                context,
                relation.object_id,
                fallback_entity=object_entity,
                fallback_type=object_type,
                include_unresolved=include_unresolved,
                with_titles=with_titles,
            )

            if not source_resolution or not target_resolution:
                continue

            source_node_id = source_resolution.node["id"]
            target_node_id = target_resolution.node["id"]

            subject_matches = (
                relation.subject_id in current_lookup_ids
                or source_node_id == current_node_id
            )
            object_matches = (
                relation.object_id in current_lookup_ids
                or target_node_id == current_node_id
            )

            if not subject_matches and not object_matches:
                continue

            source_level = current_level
            target_level = current_level

            if subject_matches and not object_matches:
                target_level = current_level + 1
            elif object_matches and not subject_matches:
                source_level = current_level + 1
            elif current_node_id not in {source_node_id, target_node_id}:
                continue

            source_added = _upsert_graph_node(
                nodes_by_id,
                lookup_ids_by_node,
                source_resolution,
                level=source_level,
                is_center=source_node_id == center_id,
                max_nodes=max_nodes,
            )
            target_added = _upsert_graph_node(
                nodes_by_id,
                lookup_ids_by_node,
                target_resolution,
                level=target_level,
                is_center=target_node_id == center_id,
                max_nodes=max_nodes,
            )

            if not source_added or not target_added:
                truncated = True
                continue

            edge = _build_graph_edge(
                relation,
                source_node_id,
                target_node_id,
            )
            edges_by_key.setdefault(edge["id"], edge)

            for node_id, node_level in (
                (source_node_id, source_level),
                (target_node_id, target_level),
            ):
                if node_id == current_node_id or node_id in visited:
                    continue

                if node_level <= depth:
                    queue.append(node_id)

    return {
        "nodes": list(nodes_by_id.values()),
        "edges": list(edges_by_key.values()),
        "meta": {
            "depth": depth,
            "max_nodes": max_nodes,
            "truncated": truncated,
        },
    }


def _validate_graph_data(data_dict: dict[str, Any]) -> list[str]:
    errors: dict[str, list[str]] = {}

    if data_dict["depth"] > GRAPH_MAX_DEPTH:
        errors["depth"] = [f"Must be between 1 and {GRAPH_MAX_DEPTH}"]

    if data_dict["max_nodes"] > GRAPH_MAX_NODES:
        errors["max_nodes"] = [f"Must be between 1 and {GRAPH_MAX_NODES}"]

    relation_types: list[str] = []
    for relation_type in data_dict.get("relation_types") or []:
        if relation_type not in Relationship.reverse_relation_type:
            errors.setdefault("relation_types", []).append(
                f"Unsupported relation type: {relation_type}"
            )
            continue

        if relation_type not in relation_types:
            relation_types.append(relation_type)

    if errors:
        raise tk.ValidationError(errors)

    return relation_types


def _entity_lookup_order(preferred_entity: str | None) -> list[str]:
    order = ["package", "organization", "group"]

    if preferred_entity in order:
        order.remove(preferred_entity)
        return [preferred_entity, *order]

    return order


def _find_entity_record(
    session: Any,
    entity: str,
    identifier: str,
) -> model.Package | model.Group | None:
    if entity == "package":
        return (
            session.query(model.Package)
            .filter(model.Package.state != "deleted")
            .filter(
                sa.or_(
                    model.Package.id == identifier,
                    model.Package.name == identifier,
                )
            )
            .one_or_none()
        )

    return (
        session.query(model.Group)
        .filter(model.Group.state != "deleted")
        .filter(model.Group.type == entity)
        .filter(
            sa.or_(
                model.Group.id == identifier,
                model.Group.name == identifier,
            )
        )
        .one_or_none()
    )


def _build_entity_url(entity: str, name: str | None) -> str | None:
    if not name:
        return None

    try:
        return tk.h.url_for(ENTITY_ROUTE_MAP[entity], id=name)
    except RuntimeError:
        return None


def _resolve_graph_node(  # noqa: PLR0913
    context: Context,
    identifier: str,
    preferred_entity: str | None = None,
    preferred_type: str | None = None,
    fallback_entity: str = "package",
    fallback_type: str = "dataset",
    include_unresolved: bool = True,
    with_titles: bool = True,
    strict: bool = False,
) -> GraphNodeResolution | None:
    session = context["session"]

    for entity in _entity_lookup_order(preferred_entity):
        record = _find_entity_record(session, entity, identifier)

        if not record:
            continue

        try:
            tk.check_access(ENTITY_SHOW_ACTION_MAP[entity], context, {"id": record.id})
        except NotAuthorized:
            if strict:
                raise
            return None

        lookup_ids = {identifier, record.id}
        if getattr(record, "name", None):
            lookup_ids.add(record.name)

        title = getattr(record, "title", None) or getattr(record, "name", None)
        if not with_titles:
            title = getattr(record, "name", None) or record.id

        return GraphNodeResolution(
            node={
                "id": f"{entity}:{record.id}",
                "entity_id": record.id,
                "name": getattr(record, "name", None),
                "title": title or record.id,
                "entity": entity,
                "entity_type": getattr(record, "type", entity),
                "resolved": True,
                "url": _build_entity_url(entity, getattr(record, "name", None)),
            },
            lookup_ids={lookup_id for lookup_id in lookup_ids if lookup_id},
        )

    if strict:
        raise NotFound(f"Object not found: {identifier}")  # noqa: TRY003

    if not include_unresolved:
        return None

    unresolved_entity = preferred_entity or fallback_entity
    unresolved_type = preferred_type or fallback_type

    return GraphNodeResolution(
        node={
            "id": f"unresolved:{identifier}",
            "entity_id": None,
            "name": identifier,
            "title": identifier,
            "entity": unresolved_entity,
            "entity_type": unresolved_type,
            "resolved": False,
            "url": None,
        },
        lookup_ids={identifier},
    )


def _get_graph_relationships(
    session: Any,
    lookup_ids: set[str],
    relation_types: list[str],
    include_reverse: bool,
) -> list[Relationship]:
    conditions = [Relationship.subject_id.in_(lookup_ids)]

    if include_reverse:
        conditions.append(Relationship.object_id.in_(lookup_ids))

    query = session.query(Relationship).filter(sa.or_(*conditions))

    if relation_types:
        query = query.filter(Relationship.relation_type.in_(relation_types))

    return query.order_by(Relationship.created_at.asc(), Relationship.id.asc()).all()


def _build_graph_edge(
    relation: Relationship,
    source_node_id: str,
    target_node_id: str,
) -> dict[str, Any]:
    if relation.relation_type == "related_to":
        source_node_id, target_node_id = sorted([source_node_id, target_node_id])
        edge_id = f"{relation.relation_type}:{source_node_id}:{target_node_id}"
    else:
        edge_id = str(relation.id)

    return {
        "id": edge_id,
        "source": source_node_id,
        "target": target_node_id,
        "relation_type": relation.relation_type,
        "directed": relation.relation_type != "related_to",
    }


def _upsert_graph_node(  # noqa: PLR0913
    nodes_by_id: dict[str, dict[str, Any]],
    lookup_ids_by_node: dict[str, set[str]],
    resolution: GraphNodeResolution,
    level: int,
    is_center: bool,
    max_nodes: int,
) -> bool:
    node_id = resolution.node["id"]

    if node_id in nodes_by_id:
        existing = nodes_by_id[node_id]
        existing["level"] = min(existing["level"], level)
        existing["is_center"] = existing["is_center"] or is_center
        existing["resolved"] = existing["resolved"] or resolution.node["resolved"]
        existing["entity_id"] = existing["entity_id"] or resolution.node["entity_id"]
        existing["name"] = existing["name"] or resolution.node["name"]
        if not existing["url"] and resolution.node["url"]:
            existing["url"] = resolution.node["url"]
        if existing["title"] == existing["name"] and resolution.node["title"]:
            existing["title"] = resolution.node["title"]

        lookup_ids_by_node[node_id].update(resolution.lookup_ids)
        return True

    if len(nodes_by_id) >= max_nodes:
        return False

    nodes_by_id[node_id] = {
        **resolution.node,
        "level": level,
        "is_center": is_center,
    }
    lookup_ids_by_node[node_id] = set(resolution.lookup_ids)
    return True
