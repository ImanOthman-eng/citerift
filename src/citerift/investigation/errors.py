"""Stable error codes of Investigation Memory.

Every refusal carries a stable code; a violated Memory invariant also names it (M-1 to M-14, or the D-043 checks).
"""

from __future__ import annotations


class InvestigationMemoryError(Exception):
    """Base class: ``code`` is stable, ``detail`` is for people."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class CanonError(InvestigationMemoryError):
    """A value outside the canonical data model (MM 2.1): CANON_INVALID or JSON_INVALID."""


class PathUnsafe(InvestigationMemoryError):
    """PATH_UNSAFE or MEMORY_ROOT_UNSAFE (S-15.3, MR-13)."""


class Busy(InvestigationMemoryError):
    """INVESTIGATION_BUSY: another process holds the investigation lock (SPEC 10.1)."""

    def __init__(self, detail: str = "") -> None:
        super().__init__("INVESTIGATION_BUSY", detail)


class BlobError(InvestigationMemoryError):
    """BLOB_MISSING, BLOB_CORRUPT or BLOB_TOO_LARGE (M-3)."""


class StorageError(InvestigationMemoryError):
    """STORAGE_ERROR: a write failed; nothing is committed by a failed write (SPEC 10.2)."""

    def __init__(self, detail: str = "") -> None:
        super().__init__("STORAGE_ERROR", detail)


class InvariantViolation(InvestigationMemoryError):
    """A Memory invariant does not hold. ``invariant`` names it (for example ``M-9``); ``seq`` is the record."""

    def __init__(self, invariant: str, code: str, detail: str, seq: int | None = None) -> None:
        super().__init__(code, f"{invariant} at seq {seq}: {detail}" if seq is not None else f"{invariant}: {detail}")
        self.invariant = invariant
        self.reason = detail
        self.seq = seq


class AppendRefused(InvariantViolation):
    """A record that would break an invariant. It is a defect of the caller and is never written (S-9.1)."""


class CorruptInvestigation(InvestigationMemoryError):
    """CORRUPT: the journal or a blob it names is invalid other than by a torn tail; read-only, never repaired
    (SPEC 8.6). ``cause`` is the violation found."""

    def __init__(self, cause: InvestigationMemoryError) -> None:
        super().__init__("CORRUPT", str(cause))
        self.cause = cause


class SpanError(InvestigationMemoryError):
    """D-043 unit anchor refusals: SPAN_INVALID, SOURCE_DIGEST_MISMATCH, ROOT_IDENTITY_MISMATCH, ANCHOR_MISMATCH."""
