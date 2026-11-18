"""Stage 04 Step 13: the naive baseline (owner decision D-069; planning package section 13).

**Rule.** A Stage 03 citation unit is flagged when any *eligible cited identifier* of it appears in a Retraction
Watch identifier field of the pinned Stage 02 index:

- eligible cited identifier: an identifier occurrence of the Stage 03 extraction that belongs to the unit
  (``unit_id`` set), has a candidate role (``primary_citation_field`` or ``identifier_link``, the roles the engine
  also uses) and a valid Stage 02 normalization (``normalization.valid`` and a ``normalized`` string); whether its
  boundary is confirmed does not matter;
- Retraction Watch identifier fields: the original-paper DOI and PubMed ID and the notice DOI and PubMed ID of an
  accepted record, as the index stores them normalized (table ``ident``, roles ``original`` and ``notice``, joined to
  ``event``);
- match: equality of (scheme, normalized value).

A flagged unit is the baseline's positive attachment. The baseline never calls the production detector or any Stage 04
module: it reads the Stage 03 extraction and the index with plain SQL. The extraction is the Stage 03 one the packet
was built from (same ``extraction_digest``).
"""

from __future__ import annotations

import sqlite3
from typing import Any

CANDIDATE_ROLES = ("primary_citation_field", "identifier_link")


def in_rw_fields(conn: sqlite3.Connection, scheme: str, norm: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM ident i JOIN event e ON e.ordinal = i.ordinal WHERE i.scheme = ? AND i.norm = ? LIMIT 1",
        (scheme, norm),
    ).fetchone()
    return row is not None


def eligible_keys(extraction: dict[str, Any]) -> dict[str, set[tuple[str, str]]]:
    out: dict[str, set[tuple[str, str]]] = {}
    for ident in extraction["identifiers"]:
        norm = ident.get("normalization") or {}
        if (
            ident.get("unit_id")
            and ident["role"] in CANDIDATE_ROLES
            and norm.get("valid")
            and isinstance(norm.get("normalized"), str)
        ):
            out.setdefault(ident["unit_id"], set()).add((ident["scheme"], norm["normalized"]))
    return out


def flagged_units(extraction: dict[str, Any], conn: sqlite3.Connection) -> set[str]:
    """Unit ids the naive baseline flags."""
    return {uid for uid, keys in eligible_keys(extraction).items() if any(in_rw_fields(conn, s, n) for s, n in keys)}
