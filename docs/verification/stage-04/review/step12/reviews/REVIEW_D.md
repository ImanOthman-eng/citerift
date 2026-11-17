# Stage 04 pre-freeze review: Reviewer D (security and boundaries)

Repository `/home/user/citerift`, HEAD `65c30bd`. Read-only review. No file inside the repository was created, changed or deleted. `git status --short` is empty, and no `.pyc` file newer than the review's first script exists outside `.venv`.

## 1 Scope and method

**What I read:**
- `src/citerift/investigation/`: `memory.py`, `journal.py`, `blobs.py`, `fsutil.py`, `lock.py`, `canonical.py`, `cli.py`, `operations.py`, `export.py`, `outputs.py`, `checkpoint.py`, `explanations.py`, `retained.py`, `schemas.py`, `lookup.py`, the controller's adapter-exception handling, and `adapters/{live,live_child,supervise,acquire,lookup,validate,plan}.py`.
- Stage 02 and Stage 03 code, only where Stage 04 calls it: `retraction/query.py` (SQL), `retraction/identifiers.py` (DOI normalisation), `wiki/verify.py`, `wiki/bundle.py`, `wiki/capture.py`.
- Documents: SPEC §8.1, §13, §15 and §16; RISK_ANALYSIS R4-27; DECISIONS D-042, D-052, D-062 and D-063; the step8, step10 and step11 closures; STEP8_BUILD_VS_ADOPT §4 and §5.

**How I ran experiments:**
- I used `/home/user/citerift/.venv/bin/python`. All scripts and data are under `/tmp/claude-0/-home-user/6e897802-8925-5c74-9e54-d0b75d7ee684/scratchpad/review-D/` (scripts in `scripts/`).
- I built a real investigation from a retained bundle: `tests/stage03/fixtures/observed/en-1372543632` with the Step 8 RW subset index. Then I ran `show`, `verify`, `replay`, `export` and `checkpoint` on it, applied tampering cases, and ran live-adapter and supervisor experiments with the test fake child. `CITERIFT_WIKI_NETWORK_LOCK` pointed into the scratch directory.
- No outbound network was used. I used no evaluation or holdout input; I avoided the `EN_CONCERN` confirmation-campaign bundle.

**Targeted tests only, not the whole suite:**
- `pytest -p no:cacheprovider tests/stage04/test_step8_live.py -k "supervisor or bound or tree or descendant or child_inside or unknown_retry"`: 6 passed.
- `-k governance` in `test_memory_storage.py`: 1 passed.

**Not done:** pip-audit needs the network, so I only inspected `pyproject.toml`. The environment runs as uid 0, and `fs.protected_symlinks=0`, `fs.protected_hardlinks=1`.

## 2 Findings

| Id | Title | Severity | Evidence | Proposed classification | Suggested fix |
|---|---|---|---|---|---|
| SD-01 | The default live-ACQUIRE work root is a predictable name in the shared temp directory. Nothing checks its owner, mode or type, and every operation on it is path-based and follows symbolic links. | MEDIUM | `adapters/live.py:149` (`gettempdir()/citerift-acquire-<uid>`), `:160-164` (`makedirs(exist_ok=True)`, `chmod`), `:164` / `:118-129` (reads planted side channels), `:172` (`mkdtemp(dir=base)`), `:212`/`:219` (path re-reads of `result.json` and `bundle`); `controller.py:347-349`. Experiment `scripts/workroot.py`: a directory pre-created by uid 65534 was accepted, its owner stayed 65534 after the run, and a planted `attempt-0-*/network.jsonl` gave `Failed(ADAPTER_INCONSISTENT, "an earlier attempt ended with a request whose Retry-After is unknown…")`, which is terminal (D-049). | 2 reliability/security defect | Validate the work root the way the memory root is validated: `lstat`, not a symlink, owner equals euid, `mode & 0o077 == 0`. Then work relative to a directory fd with `O_NOFOLLOW`. Better still, keep the per-investigation side channel in a private location tied to the memory root, or under `$XDG_RUNTIME_DIR`, rather than at a guessable `/tmp` name. |
| SD-02 | The Retry-After side channel is keyed only by the investigation key and outlives the investigation. Any later investigation of the same live request, in any memory root, can be failed terminally by it. | LOW | `live.py:160` (`base = root / investigation_key`; the key does not depend on the memory root), `:186-187` (cleaned only on success), `:124` (only the same attempt number is skipped). Experiment `scripts/shared_side.py`: investigation A was killed in flight at attempt 2 (`ACQUIRE_WALL_CLOCK_EXCEEDED`, `retry_after_known=False`). B, in another directory with the same request, then got at attempt 1: `Failed ADAPTER_INCONSISTENT …Retry-After is unknown`. | 2 reliability defect | Scope the side channel to one investigation instance, for example by including the memory root's identity or the creation record's digest. Remove it or mark it consumed when the investigation becomes terminal. Document the manual reset. |
| SD-03 | A descendant that calls `setsid` escapes the supervisor when the child exits on its own inside the bound. The documented limit names only a double-fork after the intermediate parent exits. | LOW | `supervise.py:151` reaps the leader first, then `:160` calls `tree(proc.pid)`; the parent links are already broken. Experiment `scripts/sup_exit.py`: a child spawns `Popen(..., start_new_session=True)` and exits. Result: `returncode 0 timed_out False killed () survivors ()`, and the descendant was still alive afterwards. Compare STEP8_BUILD_VS_ADOPT §4 items 4 and 6 and "Limits" ("one that called setsid while its parent lived [is] killed") and D-042 ("cannot continue network work"). Production impact is low: `wiki/capture.py` starts no process (grep for `subprocess`/`Popen` is empty). | 4 documentation inconsistency (an extension of the accepted F-11 limit, class 5) | State the normal-exit case in the documented limits. Optionally take a `/proc` snapshot of the leader's descendants before reaping it: use `os.waitid(WEXITED\|WNOWAIT)` and walk the tree before `wait()`. |
| SD-04 | Unsafe or tampered investigation directories are reported as "no investigation with that key" (exit 4) by every read-only command, while `run` reports them as invalid (exit 3). | LOW | `operations.py:221-224`: any non-MEMORY_ROOT `PathUnsafe` becomes `not_found`. `:413-414`: `run` maps it to `invalid`. Experiment `scripts/tamper.py`: a symlinked `blobs` directory, a symlinked, missing or FIFO `lock`, a group-writable investigation directory and a symlinked investigation directory all gave `verify` exit 4 `INVESTIGATION_NOT_FOUND`. A symlinked or FIFO journal and a symlinked or FIFO blob correctly gave exit 12 `corrupt`. | 1 Stage 04 correctness defect (exit classification) | Map `PathUnsafe` from an existing investigation directory to `invalid` (3) or `corrupt` (12). Reserve `not_found` for ENOENT on the key directory. |
| SD-05 | The S-15.1 static test does not cover the `adapters/` subpackage or `from citerift import governance`. | LOW | `tests/stage04/test_memory_storage.py:40,421` scan only `SRC.glob("*.py")`, which is not recursive, and check `ImportFrom.module` only. `test_step9_detector.py:490-510` covers only `dt1.py` and `adapters/detector.py`. The code is compliant today: importing all 42 `citerift.investigation.*` modules leaves no `citerift.governance*` in `sys.modules`. | 4 specification/verification inconsistency (SPEC S-15.1 says "a static test enforces it") | Use `rglob("*.py")` and also flag `ImportFrom(module="citerift", names=["governance"])`, `importlib` strings, or both. |
| SD-06 | The lock and journal are opened through hard links. A writable open truncates and rewrites whatever inode `lock` names, and appends go to every hard link of `journal.jsonl`. | INFO | `lock.py:32-55` and `journal.py:166-167`: `O_NOFOLLOW` only, no `st_nlink` check. Experiment: `lock` was hard-linked to an outside file, and `resume` rewrote that file to `'pid 11412 since 1794904606\n'`. With `protected_hardlinks=1`, no privilege boundary is crossed; a hard-link snapshot of the memory root (`cp -al`, `rsync --link-dest`) would still be modified. | 8 post-freeze concern (hardening) | Refuse `st_nlink != 1` for `lock` and `journal.jsonl` on open (report it as unsafe), or document it. |
| SD-07 | The export's "nothing replaced" guarantee is check-then-rename. `rename(2)` silently replaces an empty directory created in the window between the check and the rename. | INFO | `outputs.py:128-130`: `lexists` then `os.rename(tmp, parent/name)`. In the scratch directory, `os.rename(src_dir, empty_dst_dir)` succeeded. A pre-existing empty directory is refused by `target()` (`:55-60`); only the race window is open. | 8 post-freeze concern | Use `renameat2(RENAME_NOREPLACE)` via ctypes on Linux, or narrow the docstring wording. |
| SD-08 | Journals record absolute host paths (`memory_root`, `index_path`, `bundle_path`). This is the known A11-6, but the closure note "the paths name scratch directories only" is inaccurate. | INFO | Retained `docs/verification/stage-04/evidence/vertical-slice/results/*/journal.jsonl`: `bundle_path` = `/home/user/citerift/docs/verification/stage-03/...` (the checkout path), and `index_path`/`memory_root` include the session scratch path. STEP11_CLOSURE A11-6. Exports and checkpoints contain no paths (grep of the scratch export for `/tmp/claude`, `/home/user`: none). After freeze, runs on the owner's machine will record home-directory paths, which can contain an account name; the S-15.5 secret gate does not look for these. | 8 post-freeze concern (known A11-6) | Correct the A11-6 wording. For post-freeze retained journals, check for local paths or account names before commit. |
| SD-09 | Text and JSON output use `json.dumps(..., ensure_ascii=False)`. That escapes C0 controls (including ESC) but passes C1 controls (U+0080–U+009F) and bidi format characters (U+202E) to the terminal. | INFO | `cli.py:170,181,213,226`. Untrusted strings reaching output were traced: claim identifiers are Stage 02-normalised, and Cc/Cf characters are refused (`retraction/identifiers.py:17,71-79`). Templates are fixed (`explanations.py`). Step details are codes. A Stage 03 `BUNDLE_UNLISTED_FILE` detail carried `\x9b`, `‮` and `\x1b[2J` from a planted file name, but only as a warning, which never reached Stage 04 output. **Inference:** no current path delivers an untrusted C1 or bidi string. | 7 non-issue today (8 if new free-text fields are added) | Escape non-printable characters (`str.isprintable`) in text mode. |
| SD-10 | User-named input files are opened with plain `open()`: a FIFO blocks and a symlink is followed. The index is `lstat`-checked at VALIDATE but opened with symlinks followed in LOOKUP and identity hashing. | INFO | `checkpoint.py:79-84` (`read`), `operations.py:157` (`read_request`), `adapters/lookup.py:45` vs `validate.py:51`. `verify --checkpoint <fifo>` hung (`timeout 5` → exit 124). These paths are all self-supplied, so no boundary is crossed. | 7 non-issue (self-inflicted) | Optionally open with `O_NONBLOCK`, check `S_ISREG` on the fd, then read, as `fsutil.open_regular` already does. |

**SD-01.** This is the only Stage 04 filesystem location that skips the memory root's hardening: no owner, mode or symlink check, and every operation is by path.
- On a multi-user host, another local user who creates `/tmp/citerift-acquire-<victim uid>` first controls the victim's live ACQUIRE state. `/tmp` is cleared at boot, so that user only has to win the first creation.
- **Victim is not root.** `os.chmod(root, 0o700)` on a directory the victim does not own raises `PermissionError`; the controller turns that into terminal `ADAPTER_INCONSISTENT`, so the investigation becomes `FAILED` permanently for that key. This is inference from POSIX `chmod` semantics plus `controller.py:347-349`. The scratch directory was not traversable by uid 65534, so I did not run it.
- **Victim is root,** as in this container. The planted side channel is read and decides the outcome. I demonstrated the terminal failure; a planted Retry-After would instead defer the investigation (BLOCKED).
- **Inference, not demonstrated:** with a root victim, the attacker owns `base`. They could swap the `attempt-*` directory between `mkdtemp` and the path-based reads of `result.json` and `bundle`, and so substitute a self-consistent forged Stage 03 bundle for the requested `{wiki, revision_id}`. Stage 03 `verify_bundle` checks internal consistency, not authenticity.
- With `protected_symlinks=0`, as here, a symlinked work root is also followed by `makedirs`/`chmod`.

**SD-02.** The design note says the side channel is kept "per investigation" (`live.py:17-19`). In fact it is keyed by the deterministic key, so it is shared by every memory root holding that request.
- If an earlier run ended with a kill whose Retry-After is unknown, any fresh investigation of the same revision fails terminally with a "defect" code. That includes one started after the user deleted the old memory root.
- The terminal code `ADAPTER_INCONSISTENT` does not say why; the reason is only in the detail.
- Recovery means deleting `/tmp/citerift-acquire-<uid>/<key>`, which is not documented.
- Honouring a Retry-After across investigations is reasonable. Failing terminally is not.

**SD-03.** The timeout path is correct: SIGSTOP, then a tree walk while the leader is alive, which catches a `setsid` child. On a normal exit, `Popen.wait` reaps the leader before `tree()` runs. A direct child that called `setsid` has then been reparented and has its own session id, so it is neither found nor counted as a survivor, and the attempt is accepted. Production code does not start processes, so this is a gap in the stated limit, not an exploitable path.

**SD-04.** An adversary or an accident that changes the investigation directory's structure shows up as "absent" instead of "unsafe" or "corrupt". A user may then think nothing exists. `run` disagrees with `verify` and `show` about the same state.

**SD-05.** The requirement holds today, but its enforcing test has a blind spot exactly where the network child (`adapters/live_child.py`) lives.

**SD-06 to SD-10** are hardening and wording notes. None crosses a privilege boundary under the stated local, single-user threat model.

## 3 Checked, no finding

**Path traversal**
- Investigation keys, blob names and digests are accepted only as `^[0-9a-f]{64}$`: `fsutil.py:17-26`, `memory.py:170,236`, `blobs.py:56,94`, `cli.py:80-83`, `checkpoint.parse`.
- Artifact-set digests are schema-validated before `reconstruct` writes them (`retained.set_problem`, `acquire.py:200-210`).
- Export entries are refused unless they are fixed names or digests at most one level deep (`outputs.py:99-102`).

**Symlinks and file types inside the investigation**
- Directories are opened `O_DIRECTORY|O_NOFOLLOW` and re-checked on the fd for owner and group/other write (`fsutil.py:28-38,113-124`, `memory.py:242-249`).
- Files are opened `O_NOFOLLOW|O_NONBLOCK`, with `S_ISREG` checked on the fd (`fsutil.py:45-60`).
- Tamper results: symlinked or FIFO journal → corrupt (12); symlinked or FIFO blob → corrupt (12); symlinked investigation, blobs directory or lock → refused (exit code: see SD-04).
- A symlinked memory root is refused with `MEMORY_ROOT_UNSAFE` (exit 3).

**Permissions**
- Every file in the real run was 0600 and every directory 0700: memory directories, journal, lock and 77 blobs.
- The export directory and its subdirectories were 0700 and its files 0600 (`find`/`stat` output).
- Checkpoint files are created 0600 (`outputs.py:66`).

**Outputs outside the memory root**
- Checked on resolved paths (`outputs.py:36-63`). Writing into the memory root, or through a symlinked alias of it, gives exit 3 `OUTPUT_PATH_UNSAFE`.
- An existing target is never written through: `link` when not overwriting, `replace` (a new inode) with `--overwrite`, and a symlink target is refused.

**Atomic Memory writes**
- Blobs go temp → fsync → re-hash → `link` (never replaces) → directory fsync (`blobs.py:115-153`).
- Journal appends are truncated back on failure (`journal.py:170-192`).
- Creation is staged in a temporary directory and renamed into place (`memory.py:192-221`).

**Lock (SPEC 10.1)**
- An exclusive non-blocking kernel `flock`; the file's content is informational and never decides ownership (`lock.py`).
- While another process held `flock -x`, `show`, `verify`, `replay` and `resume` each exited 13 `INVESTIGATION_BUSY`.
- A stale lock cannot exist, because the kernel releases the lock when the holder dies.
- The lock file is never recreated; a missing lock is refused (see SD-04 for its exit code).
- `still_held` is checked before every append (`memory.py:349`).
- Read-only commands also take the exclusive lock, by design.

**Untrusted JSON**
- Strict readers: duplicate keys, BOM, lone surrogates, NaN and big integers are refused, with canonical re-encoding and `MAX_DEPTH 64` (`canonical.py:104-128`).
- Nesting fuzz at 10^2, 10^5 and 10^6 levels, against `loads_record`, `loads_blob` and the torn-tail parser, gave only `CanonError`, `RecursionError` caught, or `JOURNAL_CORRUPT`; no crash.
- Size limits: record 1 MiB, journal 512 MiB, blob 256 MiB, checkpoint 4096 B, request 1 MiB.
- Request, lookup and blob schemas are validated before use (`schemas.problems`).
- No pickle, marshal, eval or exec anywhere in the package (grep).

**SQL**
- Stage 02 queries are parameterised. The only interpolated column comes from a fixed whitelist (`retraction/query.py:193-196`), and the `WHERE` clauses are constants.
- Stage 04 issues no SQL of its own (grep `execute` in `src/citerift/investigation`: none).

**Network boundary (S-15.2, S-16.1)**
- No socket, urllib or http import in `src/citerift/investigation` (grep). `live_child.py` reaches the network only through Stage 03 `capture_revision`.
- With in-process socket refusal (`NoNetwork`), `show`, `verify`, `replay`, `export` and `checkpoint` made 0 socket attempts.
- Under `strace -f -e socket,connect`, including Stage 03's worker subprocess, `verify` and `replay` opened only `AF_UNIX` sockets to `/var/run/nscd/socket` (glibc NSS user lookup) and no inet socket; `show` opened none.

**Live child supervision on timeout**
- SIGSTOP of the process group, a `/proc` session and parent-link walk, then SIGKILL, with a start-time guard against pid reuse; the leader is reaped with `wait()` and never `waitpid(-1)`.
- The sweep is bounded, and any survivor makes the attempt fail.
- The child dies with its parent through `PR_SET_PDEATHSIG` (`live_child.py:43-53`).
- Targeted tests pass, including a descendant that called `setsid` while its parent was alive.
- After a kill, only the side channel is read; no root or blob is returned (`live.py:193-208`).

**Checkpoint wording (D-052)**
- `checkpoint.STATEMENT` is word for word the SPEC 13 sentence.
- A grep for `tamper`, `signature`, `signed`, `authentic` or `unforgeable` in `src/citerift/investigation` finds nothing.
- Every documentation hit negates such claims (STEP10_CLOSURE: "It is not a signature, authentication…").
- The checkpoint holds no time, path or host. A comparison detects only the covered prefix, as stated.

**Secrets**
- Exports contain no raw capture artifact: the observations are lookup, extraction, bundle-manifest and index-identity blobs. The raw `capture.json` and the HTML or wikitext stay as raw blobs that are never exported.
- The exported Stage 03 extraction includes cited URLs verbatim, by design.
- The child's `stdout.log` and `stderr.log` are deleted. The side channel records only API URLs and Retry-After values.
- The Step 11 closure §14 records a D-036 secret-gate scan of all 48 retained evidence files: no match.

**Dependencies and telemetry**
- Stage 04 added no runtime dependency. The Stage 04 commits change `pyproject.toml` only to add the script entry (`74d93e7`) and a ruff exclude (`906308e`). Runtime dependencies remain jsonschema, mwparserfromhell and lxml.
- No telemetry code exists.
- S-15.1 holds at runtime: no `citerift.governance` module is loaded after importing the whole package (see SD-05 for the test gap).

**Temporary bundle reconstruction for verify and replay**
- `tempfile.mkdtemp` (0700, random name); files are created `O_EXCL|O_NOFOLLOW` 0600 and removed in `finally` (`acquire.py:196-221`).

---
Status note for the caller: the review deliverable above is complete, with every finding backed by the cited files, commands or experiments in the scratch directory named in §1. As the review rules required, I did not run the full `uv run pytest`, `ruff`, `mypy` or `citerift-gov check`, so in the CLAUDE.md sense this report is:

NOT VERIFIED
