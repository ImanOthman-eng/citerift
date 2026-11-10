"""Stage 04: Investigation Memory and Workflow Controller (docs/verification/stage-04/SPECIFICATION.md 8 to 10).

Step 6 implements only the Memory layer: canonical JSON and hashing, the content-addressed blob store, the append-only
hash-chained journal, the single-writer lock, torn-tail recovery, validation of the Memory invariants (M-1 to M-14,
the parts that belong to Memory) and the Stage-04-derived unit anchor of owner decision D-043. Step 7 adds the
Workflow Controller (``workflow``: guard, fold-derived state and explanations; ``controller``: execution over the
closed adapter protocol of ``adapters``; ``ids``: step keys and child ids). The real Stage 02 and Stage 03 adapters
and the Detection Engine are later steps.

No module in this package imports ``citerift.governance`` (S-15.1).
"""

from __future__ import annotations

__version__ = "0.1.0"
