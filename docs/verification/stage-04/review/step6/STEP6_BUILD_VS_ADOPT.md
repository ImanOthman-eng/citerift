# Stage 04 Step 6: open-source leverage review for Investigation Memory

Status: Step 6 record, written before any Memory code (owner rule of 2026-11-10, message
`cmsg_018VCB51nDHP6HXmLU4ea5yP2h9GM56jQT5F4jCEcUv9zu`; Step 6 instruction
`cmsg_018VCB51nDHP6HXmLU4ea5yPHFkw4RSkx4W14idXWvzLNy`, item 1).

Baseline to beat: the design of SPEC 8 and 10, built from POSIX and standard-library primitives. These are
`os.open` with `O_NOFOLLOW`, `O_EXCL` and `O_APPEND`, `os.fsync`, `os.link` (publish without replacing), directory
`fsync`, `fcntl.flock`, `hashlib.sha256`, and `json` with strict hooks. The same primitives are already used and
reviewed in Stage 03 (`src/citerift/wiki/bundle.py`) and Stage 02.

Result: **no dependency is adopted.** Every candidate is rejected or kept as a reference only, for the reasons below.

## 1. Method (2026-11-10)

- Version, upload date, declared licence, Python requirement and direct dependencies: PyPI JSON API.
- Known vulnerabilities: the OSV API (ecosystem PyPI), queried per package.
- Maintenance: judged by the latest release date only. Commit history and issue response were not examined.
- No candidate was installed, and no code was copied.

## 2. Candidates

| Area | Candidate (release, date) | Licence; transitive | Security (OSV) | Fit for CITERIFT | Decision |
|---|---|---|---|---|---|
| File locking | filelock 4.2.10 (2026-11-09) | MIT; no dependencies | 20+ advisories (2025–2026), mostly soft and read-write lock modes: TOCTOU symlink races, stale-lock eviction, a Unix lock that truncates and chmods a file another user owns | Its Unix lock is `fcntl.flock`, the same primitive as the baseline. It adds soft locks, timeouts and Windows support, none of which CITERIFT needs, and the history shows that this surface is where the defects were | REJECT: no capability gained over `fcntl.flock` (about 30 lines); more attack surface |
| File locking | portalocker 4.4.2 (2026-10-28) | BSD-3-Clause; none | none recorded | wraps `fcntl.flock` or `lockf` on POSIX; adds Windows and Redis locks | REJECT: wraps the same call; Redis mode is a network feature |
| File locking | fasteners 0.20 (2025-08-11) | Apache-2.0; none | none recorded | inter-process locks via `fcntl`, plus reader-writer locks | REJECT: same primitive; reader-writer semantics not needed (single writer, SPEC 10.1) |
| Atomic publication | atomicwrites 1.4.1 (2022-07-08) | MIT | none recorded | write to a temporary file, then rename | REJECT: the README marks it "Unmaintained" and recommends `os.replace`. Rename-replace is also the wrong primitive: a blob must never replace an existing path (S-8.2, owner item 5), which needs `link` without replace |
| Atomic publication | safer 6.1.0 (2026-10-10) | MIT; none | none recorded | write-on-success file wrappers | REJECT: no directory `fsync`, and no rule against replacing an existing file |
| Content-addressed storage | hashfs 0.7.2 (2019-10-25, alpha) | MIT | none recorded | stores files under their hash with sharded directories | REJECT: unmaintained since 2019; no `fsync` discipline; would add a second layout beside S-8.1 `blobs/<sha256>` |
| Durable store | lmdb 3.0.0 (2026-10-02) | OpenLDAP 2.8 (permissive, not MIT/BSD/Apache); C extension | 10 advisories, all 2019 (invalid writes, divide by zero) | durable transactional key-value store | REJECT: replaces the specified append-only `journal.jsonl` with an opaque binary store, so a record could no longer be read, diffed or preserved byte for byte; C extension |
| Durable store | plyvel 1.5.1 (2024-01-15) | BSD; needs the LevelDB C++ library | none recorded | LevelDB bindings | REJECT: same reasons as lmdb; a system library dependency |
| Durable store | `sqlite3` (standard library) | public domain; no install | — | write-ahead-log journaling, transactions | REFERENCE ONLY: dependable, but the specification chose a line-per-record journal with an explicit hash chain (SPEC 8.2), and the owner's instruction keeps `journal.jsonl` authoritative |
| Canonical JSON | orjson 3.13.0 (2026-10-07) | MPL-2.0 AND (Apache-2.0 OR MIT); Rust | recursion-depth advisories (GHSA-hx9q-6w63-j58v, GHSA-pwr2-4v36-6qpr) | fast JSON with sorted keys | REJECT: MPL-2.0 needs an owner decision; its output differs from `json.dumps` (MM 2.1), which Stages 02 and 03 already use, so engine outputs and Stage 04 records would no longer share one encoding |
| Property and stateful testing | hypothesis 6.170.15 (2026-11-06) | MPL-2.0; sortedcontainers (Apache-2.0) | none recorded | stateful rule-based testing would suit the fold | REJECT for Step 6 (licence gate): MPL-2.0 is copyleft and the rule requires an owner decision first. Step 6 uses exhaustive enumeration over small state spaces (the Step 4 method) and seeded random sequences from the standard library instead. Can be revisited if the owner decides on the licence |
| Fault injection | pyfakefs 6.3.2 (2026-11-03) | Apache-2.0; none | none recorded | in-memory fake file system for tests | REJECT: it fakes `os` and `open`, so it cannot test real `fsync`, `link`, `flock` or the kernel releasing a lock when a process is killed, which is what Step 6 must prove |
| Crash-consistency research tools | ALICE, CrashMonkey (academic) | various | — | systematic crash-state exploration under power loss | REFERENCE ONLY: they need a kernel module, a block-device recorder or a FUSE layer. Step 6 injects process death at every named boundary instead, and states the power-loss limit (section 3) |

## 3. Baseline and its stated limits

The internal implementation (`src/citerift/investigation/`) uses only the standard library and the existing
`jsonschema` (DECISIONS.md D-008). Its limits are stated rather than hidden:

- Fault injection kills the process with `os._exit` at named points. This proves recovery from **process death** at
  every persistence boundary. It does not simulate **power loss or kernel crash**, where data written but not yet
  `fsync`ed can vanish or be reordered. The design follows the `fsync` order that keeps power loss safe (blob
  `fsync`, link, directory `fsync`, then the journal record and its `fsync`), but that property is argued, not
  tested.
- `fcntl.flock` is advisory and local. Network file systems are not supported (RA R4-26).
