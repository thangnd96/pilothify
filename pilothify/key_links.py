"""Link nodes in different files that name the same identifier key.

Docs refer to one thing by a key - a ticket (``ADM-15``), a bug
(``BUG-ADM-15-01``), a decision (``D-20``), a rule (``GR-06``), an ADR
(``ADR-0008``). Semantic ids are derived from the file a node came from, so the
same key written up in a test case, a QE report and a decision log becomes one
node per file, and ``explain`` on the key stops at "ambiguous". This pass ties
those nodes together with one ``same_key_as`` edge each, pointing at the
best-connected one, without merging them: each file still owns its node, so
replace-on-re-extract keeps working per file.
"""
from __future__ import annotations

import re
from collections import defaultdict

import networkx as nx

SAME_KEY_RELATION = "same_key_as"

# A key must open the label. Segments are joined by "-", the first is 1-8
# uppercase letters, and the last carries a digit: ADM-15, BUG-ADM-15-01,
# ADM-15-TC16, D-20, R-46a, ADM-ADR-0008. Bare "Q5", "T9" or "G2" are left out:
# they are local numbering that collides between unrelated documents.
_LEAD = re.compile(r"^[\s*_`\"'(\[]*([A-Za-z0-9]+(?:-[A-Za-z0-9]+)+)")
_KEY = re.compile(r"^[A-Z]{1,8}(?:-[A-Z0-9]{1,10})*-[A-Z]{0,4}\d{1,6}[a-z]?$")

# A key shared by more nodes than this is a family prefix in practice, not one
# entity; a star that size would turn it into a hub and skew clustering.
MAX_GROUP = 40


def identifier_key(label: object) -> str | None:
    """The identifier key a label opens with, or None."""
    if not isinstance(label, str):
        return None
    match = _LEAD.match(label)
    if not match:
        return None
    key = match.group(1)
    end = match.end(1)
    # "ADM-15-TC16" must not read as "ADM-15": the match is greedy over "-" runs,
    # so only a following letter or digit could still extend it.
    if end < len(label) and (label[end].isalnum() or label[end] == "_"):
        return None
    return key if _KEY.match(key) else None


def link_shared_keys(G: nx.Graph) -> int:
    """Add a same_key_as edge from each node to its key's canonical node.

    Only non-code nodes take part, and only keys that occur in two or more
    source files. Returns the number of edges added. Idempotent: an existing
    edge between the two nodes is left as it is.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for nid, attrs in G.nodes(data=True):
        if attrs.get("file_type") == "code":
            continue
        key = identifier_key(attrs.get("label"))
        if key:
            groups[key].append(nid)

    added = 0
    for key in sorted(groups):
        members = groups[key]
        if len(members) < 2 or len(members) > MAX_GROUP:
            continue
        files = {G.nodes[m].get("source_file") or "" for m in members}
        if len(files) < 2:
            continue
        # Canonical: the node already holding the most of the graph, then the
        # shortest label (closest to the bare key), then id for a stable tie-break.
        canonical = min(
            members,
            key=lambda m: (-G.degree(m), len(str(G.nodes[m].get("label") or "")), m),
        )
        for member in sorted(members):
            if member == canonical or G.has_edge(member, canonical):
                continue
            G.add_edge(
                member,
                canonical,
                relation=SAME_KEY_RELATION,
                confidence="INFERRED",
                confidence_score=0.85,
                source_file=G.nodes[member].get("source_file") or "",
                weight=1.0,
                _origin="key_link",
                _src=member,
                _tgt=canonical,
            )
            added += 1
    return added
