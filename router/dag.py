"""Directed-acyclic-graph utilities for task orchestration.

Tasks declare `depends_on` (a list of task ids). This module validates the graph is
acyclic and computes the execution order — both a flat topological order and parallel
"levels" (batches whose tasks have no unmet dependencies, so they can run concurrently
in the map phase). Pure logic, no IO — fully unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Node:
    id: str
    depends_on: tuple[str, ...] = field(default_factory=tuple)


class CycleError(ValueError):
    """Raised when the dependency graph contains a cycle."""


def _index(nodes: list[Node]) -> dict[str, Node]:
    idx: dict[str, Node] = {}
    for n in nodes:
        if n.id in idx:
            raise ValueError(f"duplicate task id: {n.id}")
        idx[n.id] = n
    return idx


def validate(nodes: list[Node]) -> None:
    """Raise if any dependency is unknown or the graph has a cycle."""
    idx = _index(nodes)
    for n in nodes:
        for dep in n.depends_on:
            if dep not in idx:
                raise ValueError(f"task '{n.id}' depends on unknown task '{dep}'")
    # Cycle check is implicit in topological_order; call it to surface errors.
    topological_order(nodes)


def topological_order(nodes: list[Node]) -> list[str]:
    """Kahn's algorithm — returns task ids in a valid execution order."""
    idx = _index(nodes)
    indeg = {nid: 0 for nid in idx}
    for n in nodes:
        for dep in n.depends_on:
            if dep in indeg:
                indeg[n.id] += 1
    # Deterministic: process ready nodes in sorted id order.
    ready = sorted([nid for nid, d in indeg.items() if d == 0])
    order: list[str] = []
    while ready:
        nid = ready.pop(0)
        order.append(nid)
        for n in nodes:
            if nid in n.depends_on:
                indeg[n.id] -= 1
                if indeg[n.id] == 0:
                    ready.append(n.id)
        ready.sort()
    if len(order) != len(idx):
        raise CycleError("dependency cycle detected")
    return order


def levels(nodes: list[Node]) -> list[list[str]]:
    """Group task ids into dependency levels. Each inner list can run in parallel."""
    idx = _index(nodes)
    validate(nodes)
    done: set[str] = set()
    out: list[list[str]] = []
    remaining = set(idx)
    while remaining:
        batch = sorted(
            nid for nid in remaining if all(d in done for d in idx[nid].depends_on)
        )
        if not batch:  # pragma: no cover - validate() already rules this out
            raise CycleError("dependency cycle detected")
        out.append(batch)
        done.update(batch)
        remaining -= set(batch)
    return out
