from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
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
OBJECT_NOT_FOUND_MESSAGE = "Object not found: {identifier}"


class GraphNodeResolution(NamedTuple):
    node: dict[str, Any]
    lookup_ids: set[str]


class GraphFrontier(NamedTuple):
    level: int
    node_ids: list[str]
    lookup_ids: set[str]
    lookup_ids_by_node: dict[str, set[str]]


class GraphResolveOptions(NamedTuple):
    preferred_entity: str | None = None
    preferred_type: str | None = None
    fallback_entity: str = "package"
    fallback_type: str = "dataset"
    include_unresolved: bool = True
    with_titles: bool = True
    strict: bool = False


class ResolvedEntityRecord(NamedTuple):
    entity: str
    record: model.Package | model.Group


class GraphRelationNodes(NamedTuple):
    source_resolution: GraphNodeResolution
    target_resolution: GraphNodeResolution
    source_node_id: str
    target_node_id: str


@dataclass
class GraphCaches:
    resolution_cache: dict[
        tuple[str, GraphResolveOptions],
        GraphNodeResolution | None | Exception,
    ] = field(default_factory=dict)
    entity_record_cache: dict[
        tuple[str, str],
        model.Package | model.Group | None,
    ] = field(default_factory=dict)
    access_cache: dict[tuple[str, str], NotAuthorized | None] = field(
        default_factory=dict
    )


@dataclass
class GraphState:
    center_id: str
    max_nodes: int
    nodes_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    lookup_ids_by_node: dict[str, set[str]] = field(default_factory=dict)
    edges_by_key: dict[str, dict[str, Any]] = field(default_factory=dict)
    visited: set[str] = field(default_factory=set)
    queue: deque[str] = field(default_factory=deque)
    truncated: bool = False


class GraphRuntime(NamedTuple):
    context: Context
    relation_types: list[str]
    include_reverse: bool
    depth: int
    resolve_options: GraphResolveOptions
    caches: GraphCaches


def get_actions():
    return {
        "relationship_graph": relationship_graph,
    }


@tk.side_effect_free
@validate(schema.graph)
def relationship_graph(context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    tk.check_access("relationship_graph", context, data_dict)

    runtime = _build_graph_runtime(context, data_dict)
    state = _initialize_graph_state(
        data_dict["object_id"],
        data_dict["max_nodes"],
        runtime,
    )

    while frontier := _pop_graph_frontier(
        state.queue,
        state.nodes_by_id,
        state.lookup_ids_by_node,
        state.visited,
    ):
        if frontier.level >= runtime.depth:
            continue

        _process_graph_frontier(runtime, state, frontier)

    return {
        "nodes": list(state.nodes_by_id.values()),
        "edges": list(state.edges_by_key.values()),
        "meta": {
            "depth": runtime.depth,
            "max_nodes": state.max_nodes,
            "truncated": state.truncated,
        },
    }


def _build_graph_runtime(context: Context, data_dict: dict[str, Any]) -> GraphRuntime:
    object_entity = data_dict["object_entity"]
    object_type = data_dict["object_type"]

    return GraphRuntime(
        context=context,
        relation_types=_validate_graph_data(data_dict),
        include_reverse=data_dict["include_reverse"],
        depth=data_dict["depth"],
        resolve_options=GraphResolveOptions(
            fallback_entity=object_entity,
            fallback_type=object_type,
            include_unresolved=data_dict["include_unresolved"],
            with_titles=data_dict["with_titles"],
        ),
        caches=GraphCaches(),
    )


def _initialize_graph_state(
    object_id: str,
    max_nodes: int,
    runtime: GraphRuntime,
) -> GraphState:
    center_options = GraphResolveOptions(
        preferred_entity=runtime.resolve_options.fallback_entity,
        preferred_type=runtime.resolve_options.fallback_type,
        fallback_entity=runtime.resolve_options.fallback_entity,
        fallback_type=runtime.resolve_options.fallback_type,
        include_unresolved=False,
        with_titles=runtime.resolve_options.with_titles,
        strict=True,
    )
    center_resolution = _resolve_graph_node(
        runtime.context,
        object_id,
        center_options,
        runtime.caches,
    )
    state = GraphState(center_id=center_resolution.node["id"], max_nodes=max_nodes)

    _upsert_graph_node(
        state,
        center_resolution,
        level=0,
        is_center=True,
    )
    state.queue.append(state.center_id)

    return state


def _process_graph_frontier(
    runtime: GraphRuntime,
    state: GraphState,
    frontier: GraphFrontier,
) -> None:
    for relation in _get_graph_relationships(
        runtime.context["session"],
        frontier.lookup_ids,
        runtime.relation_types,
        runtime.include_reverse,
    ):
        _process_graph_relation(runtime, state, frontier, relation)


def _process_graph_relation(
    runtime: GraphRuntime,
    state: GraphState,
    frontier: GraphFrontier,
    relation: Relationship,
) -> None:
    relation_nodes = _resolve_relation_nodes(runtime, relation)

    if relation_nodes is None:
        return

    for current_node_id in _matching_frontier_node_ids(
        frontier,
        relation,
        relation_nodes,
    ):
        current_lookup_ids = frontier.lookup_ids_by_node[current_node_id]
        levels = _relation_levels(
            current_node_id,
            current_lookup_ids,
            frontier.level,
            relation,
            relation_nodes,
        )

        if levels is None:
            continue

        if not _record_graph_relation(state, relation, relation_nodes, levels):
            continue

        _enqueue_graph_nodes(
            state,
            relation_nodes,
            levels,
            current_node_id,
            runtime.depth,
        )


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


def _pop_graph_frontier(
    queue: deque[str],
    nodes_by_id: dict[str, dict[str, Any]],
    lookup_ids_by_node: dict[str, set[str]],
    visited: set[str],
) -> GraphFrontier | None:
    while queue:
        current_node_id = queue.popleft()

        if current_node_id in visited:
            continue

        current_level = nodes_by_id[current_node_id]["level"]
        node_ids = [current_node_id]
        frontier_lookup_ids_by_node = {
            current_node_id: lookup_ids_by_node[current_node_id],
        }

        visited.add(current_node_id)

        while queue and nodes_by_id[queue[0]]["level"] == current_level:
            node_id = queue.popleft()

            if node_id in visited:
                continue

            node_ids.append(node_id)
            frontier_lookup_ids_by_node[node_id] = lookup_ids_by_node[node_id]

            visited.add(node_id)

        frontier_lookup_ids = set().union(*frontier_lookup_ids_by_node.values())

        return GraphFrontier(
            level=current_level,
            node_ids=node_ids,
            lookup_ids=frontier_lookup_ids,
            lookup_ids_by_node=frontier_lookup_ids_by_node,
        )

    return None


def _load_entity_record(
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


def _find_entity_record(
    session: Any,
    entity: str,
    identifier: str,
    caches: GraphCaches,
) -> model.Package | model.Group | None:
    cache_key = (entity, identifier)

    if cache_key not in caches.entity_record_cache:
        caches.entity_record_cache[cache_key] = _load_entity_record(
            session,
            entity,
            identifier,
        )

    return caches.entity_record_cache[cache_key]


def _get_entity_access_error(
    context: Context,
    entity: str,
    record_id: str,
    caches: GraphCaches,
) -> NotAuthorized | None:
    cache_key = (entity, record_id)

    if cache_key in caches.access_cache:
        return caches.access_cache[cache_key]

    try:
        tk.check_access(ENTITY_SHOW_ACTION_MAP[entity], context, {"id": record_id})
    except NotAuthorized as err:
        caches.access_cache[cache_key] = err
    else:
        caches.access_cache[cache_key] = None

    return caches.access_cache[cache_key]


def _build_entity_url(entity: str, name: str | None) -> str | None:
    if not name:
        return None

    try:
        return tk.h.url_for(ENTITY_ROUTE_MAP[entity], id=name)
    except RuntimeError:
        return None


def _resolve_graph_node(
    context: Context,
    identifier: str,
    options: GraphResolveOptions,
    caches: GraphCaches,
) -> GraphNodeResolution | None:
    cache_key = (identifier, options)

    if cache_key in caches.resolution_cache:
        cached = caches.resolution_cache[cache_key]

        if isinstance(cached, Exception):
            raise cached

        return cached

    entity_record = _find_resolved_entity_record(
        context,
        identifier,
        options.preferred_entity,
        options.strict,
        caches,
    )
    if entity_record is not None:
        resolution = _build_resolved_graph_node(
            identifier,
            entity_record,
            options.with_titles,
        )
    else:
        resolution = _build_fallback_graph_node(identifier, options)

    caches.resolution_cache[cache_key] = resolution
    return resolution


def _find_resolved_entity_record(
    context: Context,
    identifier: str,
    preferred_entity: str | None,
    strict: bool,
    caches: GraphCaches,
) -> ResolvedEntityRecord | None:
    session = context["session"]

    for entity in _entity_lookup_order(preferred_entity):
        record = _find_entity_record(session, entity, identifier, caches)

        if record is None:
            continue

        access_error = _get_entity_access_error(context, entity, record.id, caches)
        if access_error is not None:
            if strict:
                raise access_error
            return None

        return ResolvedEntityRecord(entity, record)

    return None


def _build_resolved_graph_node(
    identifier: str,
    entity_record: ResolvedEntityRecord,
    with_titles: bool,
) -> GraphNodeResolution:
    entity = entity_record.entity
    record = entity_record.record
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


def _build_fallback_graph_node(
    identifier: str,
    options: GraphResolveOptions,
) -> GraphNodeResolution | None:
    if options.strict:
        raise NotFound(OBJECT_NOT_FOUND_MESSAGE.format(identifier=identifier))

    if not options.include_unresolved:
        return None

    return GraphNodeResolution(
        node={
            "id": f"unresolved:{identifier}",
            "entity_id": None,
            "name": identifier,
            "title": identifier,
            "entity": options.preferred_entity or options.fallback_entity,
            "entity_type": options.preferred_type or options.fallback_type,
            "resolved": False,
            "url": None,
        },
        lookup_ids={identifier},
    )


def _resolve_relation_nodes(
    runtime: GraphRuntime,
    relation: Relationship,
) -> GraphRelationNodes | None:
    source_resolution = _resolve_graph_node(
        runtime.context,
        relation.subject_id,
        runtime.resolve_options,
        runtime.caches,
    )
    target_resolution = _resolve_graph_node(
        runtime.context,
        relation.object_id,
        runtime.resolve_options,
        runtime.caches,
    )

    if source_resolution is None or target_resolution is None:
        return None

    return GraphRelationNodes(
        source_resolution=source_resolution,
        target_resolution=target_resolution,
        source_node_id=source_resolution.node["id"],
        target_node_id=target_resolution.node["id"],
    )


def _matching_frontier_node_ids(
    frontier: GraphFrontier,
    relation: Relationship,
    relation_nodes: GraphRelationNodes,
) -> list[str]:
    endpoint_ids = {relation_nodes.source_node_id, relation_nodes.target_node_id}

    return [
        node_id
        for node_id in frontier.node_ids
        if relation.subject_id in frontier.lookup_ids_by_node[node_id]
        or relation.object_id in frontier.lookup_ids_by_node[node_id]
        or node_id in endpoint_ids
    ]


def _relation_levels(
    current_node_id: str,
    current_lookup_ids: set[str],
    current_level: int,
    relation: Relationship,
    relation_nodes: GraphRelationNodes,
) -> tuple[int, int] | None:
    subject_matches = (
        relation.subject_id in current_lookup_ids
        or relation_nodes.source_node_id == current_node_id
    )
    object_matches = (
        relation.object_id in current_lookup_ids
        or relation_nodes.target_node_id == current_node_id
    )

    if not subject_matches and not object_matches:
        return None

    source_level = current_level
    target_level = current_level

    if subject_matches and not object_matches:
        target_level = current_level + 1
    elif object_matches and not subject_matches:
        source_level = current_level + 1
    elif current_node_id not in {
        relation_nodes.source_node_id,
        relation_nodes.target_node_id,
    }:
        return None

    return source_level, target_level


def _record_graph_relation(
    state: GraphState,
    relation: Relationship,
    relation_nodes: GraphRelationNodes,
    levels: tuple[int, int],
) -> bool:
    source_level, target_level = levels
    source_added = _upsert_graph_node(
        state,
        relation_nodes.source_resolution,
        level=source_level,
        is_center=relation_nodes.source_node_id == state.center_id,
    )
    target_added = _upsert_graph_node(
        state,
        relation_nodes.target_resolution,
        level=target_level,
        is_center=relation_nodes.target_node_id == state.center_id,
    )

    if not source_added or not target_added:
        state.truncated = True
        return False

    edge = _build_graph_edge(
        relation,
        relation_nodes.source_node_id,
        relation_nodes.target_node_id,
    )
    state.edges_by_key.setdefault(edge["id"], edge)
    return True


def _enqueue_graph_nodes(
    state: GraphState,
    relation_nodes: GraphRelationNodes,
    levels: tuple[int, int],
    current_node_id: str,
    depth: int,
) -> None:
    for node_id, node_level in (
        (relation_nodes.source_node_id, levels[0]),
        (relation_nodes.target_node_id, levels[1]),
    ):
        if node_id == current_node_id or node_id in state.visited:
            continue

        if node_level <= depth:
            state.queue.append(node_id)


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


def _upsert_graph_node(
    state: GraphState,
    resolution: GraphNodeResolution,
    level: int,
    is_center: bool,
) -> bool:
    node_id = resolution.node["id"]

    if node_id in state.nodes_by_id:
        existing = state.nodes_by_id[node_id]
        existing["level"] = min(existing["level"], level)
        existing["is_center"] = existing["is_center"] or is_center
        existing["resolved"] = existing["resolved"] or resolution.node["resolved"]
        existing["entity_id"] = existing["entity_id"] or resolution.node["entity_id"]
        existing["name"] = existing["name"] or resolution.node["name"]
        if not existing["url"] and resolution.node["url"]:
            existing["url"] = resolution.node["url"]
        if existing["title"] == existing["name"] and resolution.node["title"]:
            existing["title"] = resolution.node["title"]

        state.lookup_ids_by_node[node_id].update(resolution.lookup_ids)
        return True

    if len(state.nodes_by_id) >= state.max_nodes:
        return False

    state.nodes_by_id[node_id] = {
        **resolution.node,
        "level": level,
        "is_center": is_center,
    }
    state.lookup_ids_by_node[node_id] = set(resolution.lookup_ids)
    return True
