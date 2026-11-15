"""Link doc nodes that name an HTTP endpoint to the handler serving it.

Extractors stamp ``attributes["route"]`` on handler nodes (``POST
/api/v1/game/cinema/screen/playback``). Specs, RFCs and QE reports name the same
endpoints in prose, often without the version prefix (``PUT
/me/social/shares/{postId}``). This pass matches the two, so a question that
starts from a doc reaches the code that serves it and a question that starts
from a handler reaches what was written about it.
"""
from __future__ import annotations

import re
from collections import defaultdict

import networkx as nx

ROUTE_RELATION = "references_route"

_VERBS = ("GET", "POST", "PUT", "PATCH", "DELETE")
_MENTION = re.compile(
    r"(?:\b(GET|POST|PUT|PATCH|DELETE)\s+)?(/[A-Za-z0-9_.~{}:\-]+(?:/[A-Za-z0-9_.~{}:\-]+)+)(/?\*)?"
)
# A doc node naming more endpoints than this is a listing, not a reference.
_MAX_LINKS_PER_NODE = 6


def _segments(path: str) -> tuple[str, ...]:
    """Path segments with every parameter (``{id}``, ``:id``) folded to ``{}``."""
    out = []
    for part in path.strip("/").split("/"):
        if not part:
            continue
        if (part.startswith("{") and part.endswith("}")) or part.startswith(":"):
            out.append("{}")
        else:
            out.append(part.lower())
    return tuple(out)


def _parse_route(route: str) -> list[tuple[str | None, tuple[str, ...]]]:
    parsed = []
    for entry in route.split(", "):
        verb, _, path = entry.partition(" ")
        if verb not in _VERBS:
            verb, path = None, entry
        segs = _segments(path)
        if segs:
            parsed.append((verb, segs))
    return parsed


def link_routes(G: nx.Graph) -> int:
    """Add a references_route edge from each doc node to the handler it names.

    A mention matches a route when its segments equal the route's (EXTRACTED)
    or end it, two segments or more, under exactly one full path (INFERRED
    0.95). A stated verb must agree. Globs (``/ctrl/**``) never match.
    Returns the number of edges added.
    """
    by_path: dict[tuple[str, ...], list[tuple[str | None, str]]] = defaultdict(list)
    for nid, attrs in G.nodes(data=True):
        extra = attrs.get("attributes")
        route = extra.get("route") if isinstance(extra, dict) else None
        if isinstance(route, str) and route:
            for verb, segs in _parse_route(route):
                by_path[segs].append((verb, nid))
    if not by_path:
        return 0
    by_tail: dict[tuple[str, ...], set[tuple[str, ...]]] = defaultdict(set)
    for segs in by_path:
        for start in range(1, len(segs) - 1):
            by_tail[segs[start:]].add(segs)

    added = 0
    for nid, attrs in list(G.nodes(data=True)):
        if attrs.get("file_type") == "code":
            continue
        text = " ".join(
            t for t in (attrs.get("label"), attrs.get("rationale")) if isinstance(t, str)
        )
        if "/" not in text:
            continue
        targets: dict[str, bool] = {}
        for match in _MENTION.finditer(text):
            if match.group(3):
                continue
            verb, segs = match.group(1), _segments(match.group(2))
            if segs in by_path:
                full, exact = segs, True
            elif segs in by_tail:
                fulls = by_tail[segs]
                if len(fulls) != 1:
                    continue
                full, exact = next(iter(fulls)), False
            else:
                # A route mounted under a prefix set in another file is shorter
                # than the doc's full path: match its longest tail of 2+ segments.
                full = next((segs[s:] for s in range(1, len(segs) - 1) if segs[s:] in by_path), None)
                if full is None:
                    continue
                exact = False
            for route_verb, handler in by_path[full]:
                if verb and route_verb and verb != route_verb:
                    continue
                targets[handler] = targets.get(handler, False) or exact
        if not targets or len(targets) > _MAX_LINKS_PER_NODE:
            continue
        for handler, exact in sorted(targets.items()):
            if handler == nid or G.has_edge(nid, handler):
                continue
            G.add_edge(
                nid,
                handler,
                relation=ROUTE_RELATION,
                confidence="EXTRACTED" if exact else "INFERRED",
                confidence_score=1.0 if exact else 0.95,
                source_file=attrs.get("source_file") or "",
                weight=1.0,
                _origin="route_link",
                _src=nid,
                _tgt=handler,
            )
            added += 1
    return added
