"""Periodic quotient graphs: translations are part of an edge's identity."""
from __future__ import annotations

import copy
from collections import defaultdict, deque

import numpy as np

from .io import InputError


def canonical(a, b, shift):
    s = tuple(int(x) for x in shift)
    return min((int(a), int(b), s), (int(b), int(a), tuple(-x for x in s)))


def adjacency(edges):
    neighbors = defaultdict(list)
    for a, b, s in edges:
        neighbors[a].append((b, np.array(s, dtype=int)))
        neighbors[b].append((a, -np.array(s, dtype=int)))
    return neighbors


def simplify_graph(graph, contract_linkers=True):
    """Prune caps; suppress ditopic units without losing periodic self edges."""
    nodes = {int(n["id"]): copy.deepcopy(n) for n in graph["nodes"]}
    edges = {canonical(e["a"], e["b"], e["shift"]) for e in graph["edges"]}
    if any(a not in nodes or b not in nodes for a, b, _ in edges):
        raise InputError("Topology edge references an unknown node")
    caps = {k for k, n in nodes.items() if n.get("kind") == "cap"}
    edges = {e for e in edges if e[0] not in caps and e[1] not in caps}
    nodes = {k: n for k, n in nodes.items() if k not in caps}
    contracted = []
    if contract_linkers:
        while True:
            neighbors = adjacency(edges)
            removable = next((k for k in sorted(nodes)
                              if len(neighbors[k]) == 2
                              and all(other != k for other, _ in neighbors[k])), None)
            if removable is None:
                break
            (a, sa), (b, sb) = neighbors[removable]
            edges = {e for e in edges if removable not in e[:2]}
            edge = canonical(a, b, sb - sa)
            if edge != (a, a, (0, 0, 0)):
                edges.add(edge)
            contracted.append(removable)
            nodes.pop(removable)
    neighbors = adjacency(edges)
    for k, node in nodes.items():
        node["degree"] = len(neighbors[k])
    return {"nodes": list(nodes.values()),
            "edges": [{"a": a, "b": b, "shift": list(s)} for a, b, s in sorted(edges)],
            "contracted_unit_ids": contracted, "removed_cap_ids": sorted(caps)}


def periodic_dimensions(graph):
    """Rank of closed-walk lattice translations for each quotient component."""
    edges = {canonical(e["a"], e["b"], e["shift"]) for e in graph["edges"]}
    neighbors = adjacency(edges)
    unseen = {int(n["id"]) for n in graph["nodes"]}
    result = []
    while unseen:
        root = min(unseen)
        gauge = {root: np.zeros(3, dtype=int)}
        queue = deque([root])
        cycles = []
        while queue:
            a = queue.popleft()
            for b, shift in neighbors[a]:
                trial = gauge[a] + shift
                if b in gauge:
                    cycles.append(trial - gauge[b])
                else:
                    gauge[b] = trial
                    queue.append(b)
        unseen -= set(gauge)
        rank = int(np.linalg.matrix_rank(np.array(cycles))) if cycles else 0
        result.append({"node_ids": sorted(gauge), "dimension": rank})
    return result


def unwrap_nonperiodic_axes(graph):
    """Choose a continuous image gauge along nonperiodic lattice axes.

    A layer at z=0 may have numerical coordinates near z=1 for half its atoms.
    A finite one-layer crop would sever every such bond. Closed-walk translations
    identify axes along which image shifts are pure gauge, not lattice periodicity.
    """
    graph = copy.deepcopy(graph)
    edges = {canonical(e["a"], e["b"], e["shift"]) for e in graph["edges"]}
    neighbors = adjacency(edges)
    remaining = {int(n["id"]) for n in graph["nodes"]}
    shifts = {}
    while remaining:
        root = min(remaining)
        gauge = {root: np.zeros(3, dtype=int)}
        queue, cycles = deque([root]), []
        while queue:
            a = queue.popleft()
            for b, offset in neighbors[a]:
                trial = gauge[a] + offset
                if b in gauge:
                    cycles.append(trial - gauge[b])
                else:
                    gauge[b] = trial
                    queue.append(b)
        remaining -= set(gauge)
        nonperiodic = ~np.any(np.asarray(cycles) != 0, axis=0) if cycles else np.ones(3, dtype=bool)
        for i, image in gauge.items():
            shifts[i] = np.where(nonperiodic, image, 0)
    for node in graph["nodes"]:
        offset = shifts[int(node["id"])]
        node["fractional"] = (np.asarray(node["fractional"]) + offset).tolist()
        if "ports_fractional" in node:
            node["ports_fractional"] = [(np.asarray(p) + offset).tolist()
                                        for p in node["ports_fractional"]]
    for edge in graph["edges"]:
        edge["shift"] = (np.asarray(edge["shift"]) + shifts[int(edge["a"])]
                         - shifts[int(edge["b"])]).tolist()
    return graph, {str(k): v.tolist() for k, v in shifts.items() if np.any(v)}
