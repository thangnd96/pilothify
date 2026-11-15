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

# ALL (Express `router.all`, NestJS `@All`) serves every verb.
_VERBS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "ALL")
_MENTION = re.compile(
    r"(?:\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+)?(/[A-Za-z0-9_.~{}:\-]+(?:/[A-Za-z0-9_.~{}:\-]+)+)(/?\*)?"
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


def _verb_agrees(stated: str | None, served: str | None) -> bool:
    return not stated or not served or served == "ALL" or stated == served


def _verb_matches(stated: str | None, handlers: list[tuple[str | None, str]]) -> bool:
    return any(_verb_agrees(stated, served) for served, _ in handlers)


def link_routes(G: nx.Graph) -> int:
    """Add a references_route edge from each doc node to the handler it names.

    A mention matches a route when its segments equal the route's (EXTRACTED),
    end it, two segments or more, under exactly one full path, or are longer
    and end with a route of two segments or more (both INFERRED 0.95). A stated
    verb must agree; ALL serves every verb. Globs (``/ctrl/**``) never match.
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
                # than the doc's full path: match its longest tail of 2+ segments
                # whose verb agrees. A path under another host (`https://h/...`)
                # is someone else's API, so it never takes this branch.
                if text[max(0, match.start(2) - 1):match.start(2)] == "/" or "." in segs[0]:
                    continue
                full = next((segs[s:] for s in range(1, len(segs) - 1)
                             if segs[s:] in by_path and _verb_matches(verb, by_path[segs[s:]])), None)
                if full is None:
                    continue
                exact = False
            for route_verb, handler in by_path[full]:
                if not _verb_agrees(verb, route_verb):
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
