"""Stage 04 pre-registration P2 (owner decision D-076): the P2 tooling, on exposed development fixtures only.

The tools live in ``docs/verification/stage-04/evaluation-p2/tools`` (``p2_*.py``), outside ``src/``, derived from
the historical Step 13 tools, which stay unchanged with the historical P. Fixtures: the design-exposed bundle of VS-1
(MMR vaccine, Wakefield), the attributed Step 8 Retraction Watch subset index, synthetic frames, labels and index
rows. No P2 holdout article exists: no seed, no draw, no capture, no label and no prediction is made or read here.
"""

from __future__ import annotations

import ast
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import step8_support as S8

REPO = Path(__file__).resolve().parents[2]
P2 = REPO / "docs/verification/stage-04/evaluation-p2"
TOOLS = P2 / "tools"
HISTORICAL = REPO / "docs/verification/stage-04/evaluation"
sys.path.insert(0, str(TOOLS))

import p2_common as C  # noqa: E402
import p2_draw as DR  # noqa: E402
import p2_frame as FR  # noqa: E402
import p2_labels as LB  # noqa: E402
import p2_manifest as MF  # noqa: E402
import p2_packets as PK  # noqa: E402
import p2_run as RN  # noqa: E402
import p2_score as SC  # noqa: E402

from citerift.investigation import __version__, dt1  # noqa: E402

PARAMS = C.read_json(P2 / "PARAMETERS.json")
HISTORICAL_PARAMS = C.read_json(HISTORICAL / "PARAMETERS.json")
FROZEN = "28ba6467c7005eec7bf51869974719a402059ca7"
FROZEN_TREE = "45c52da459b09597f105d6e4abd8ab00332c6799"
FREEZE_DIGEST = "d9db2704c495459acc3487b0e656d27b386f124cae4e3bdf36b1e059a2c61c13"
EXPOSURE_SHA = "b2a2a937a6ec245135a3495dad9e458e1b6a64e69cdf2eb4099794c5ab45e67b"
HISTORICAL_P = "4eded723bbb464c247b31e675d2f2fc7d16133328d55925c9a787801efd1098a"
PREREG_COMMIT = "827ac1aa1d9d16d444d4860e4119f8633d8e802e"
CAMPAIGN_COMMIT = "1064113902c674f1c61dcb7eda33afe40350ca71"
SUPERSEDED = "b5bf8edfcb6f7c747a9c751bd1d402858eecbcf0"
NAME = "en-1381772671"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True, text=True).stdout


def _require_history() -> None:
    for commit in (FROZEN, PREREG_COMMIT, CAMPAIGN_COMMIT, SUPERSEDED):
        probe = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=REPO, check=False)
        if probe.returncode != 0:
            pytest.fail(f"commit {commit} is missing: the P2 checks need the full history (no shallow clone)")


# ------------------------------------------------------------------------------------------------ boundaries


@pytest.mark.unit
def test_p2_tools_are_outside_src_and_never_imported_by_production() -> None:
    for path in (REPO / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "p2_" not in text and "evaluation-p2" not in text, path
    for path in TOOLS.glob("p2_*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not node.value.startswith("src/"), (path.name, node.value)


@pytest.mark.unit
def test_p2_parameters_pin_the_accepted_freeze2_engine() -> None:
    frozen = PARAMS["frozen_engine"]
    assert (frozen["content_commit"], frozen["tree"], frozen["freeze_manifest_digest"]) == (
        FROZEN,
        FROZEN_TREE,
        FREEZE_DIGEST,
    )
    assert frozen["identity"] == {
        "engine_version": "0.3.0",
        "package_version": "0.3.0",
        "table_version": "dt-2",
        "schema_version": "4.0.0",
        "claim_schema_version": "3.0.0",
        "plan_version": "plan-1",
        "detector_identity": "citerift-dt1-detector/3 (dt-2)",
    }
    assert PARAMS["exposure"]["manifest_sha256"] == EXPOSURE_SHA
    assert PARAMS["exposure"]["manifest_path"].startswith("docs/verification/stage-04/freeze-2/")


@pytest.mark.unit
def test_p2_keeps_the_historical_gates_allocation_expansion_and_retrieval() -> None:
    """D-076 sections 5 and 6: gates not relaxed or tuned; the accepted sampling philosophy kept unchanged."""
    for key in ("gates", "sampling", "acquisition", "retrieval", "annotation", "retraction_watch"):
        assert PARAMS[key] == HISTORICAL_PARAMS[key], key
    assert PARAMS["gates"] == {
        "min_positive_units": 30,
        "max_false_attachment_upper_95": 0.10,
        "min_negative_units": 60,
    }
    assert PARAMS["frame"]["exclude_listed_tier"] is False  # D-070 kept


# ------------------------------------------------------------------------------------------------ engine identity


# Final corrective cycle (D-083), owner decision D-084 (decision card "Allow the two pre-registered test files to
# check the old engines from git?", option "Amend both, D-074 style", chosen 2026-11-20): the working tree is no
# longer the freeze-2 engine (dt-3 replaced it), so the frozen-engine checks are proved in their historical context.
# P2's own tools at the P2 commit run, as a ``python -I`` subprocess, in a worktree of that commit with its own ``src``
# first on the path. P2, its files, its runs and its scores are not changed; the P2 bytes of this file are proved from
# git.

P2_COMMIT = "10cc9d8267942d625d0d32a4b4b72101155c0d06"
P2_DIGEST = "5d323a67d89a521384772ce7a566520e862715ce9389227f428ff8439f74f75a"
MANIFEST_REL = "docs/verification/stage-04/evaluation-p2/PREREGISTRATION_MANIFEST.json"
THIS_TEST = "tests/stage04/test_p2_evaluation.py"
HISTORICAL_PROBE = """
import json, sys
from pathlib import Path
wt = Path.cwd()
sys.path[:0] = [str(wt / "src"), str(wt / "docs/verification/stage-04/evaluation-p2/tools")]
import citerift, p2_common as C, p2_manifest as MF, p2_run as RN
assert Path(citerift.__file__).resolve().is_relative_to(wt.resolve()), citerift.__file__
out = {"engine_check": C.engine_check(), "frozen_check": RN.frozen_check(C.read_json(C.PARAMETERS))}
out["manifest_equal"] = MF.build() == C.read_json(MF.MANIFEST)
print(json.dumps(out))
"""
# One mutation of P2's parameters (argv[1]: JSON ``{"path", "value", "bad_tree", "runner"}``) checked by P2's own
# engine check (or runner guard) at the P2 commit; ``bad_tree`` makes ``rev-parse HEAD:<first checked path>`` name
# another tree (the committed-tree branch of the check). Prints the refusal message, or null when accepted.
MUTATION_PROBE = """
import json, sys
from pathlib import Path
wt = Path.cwd()
sys.path[:0] = [str(wt / "src"), str(wt / "docs/verification/stage-04/evaluation-p2/tools")]
import citerift, p2_common as C, p2_run as RN
assert Path(citerift.__file__).resolve().is_relative_to(wt.resolve()), citerift.__file__
spec = json.loads(sys.argv[1])
params = C.read_json(C.PARAMETERS)
node = params
for k in spec["path"][:-1]:
    node = node[k]
if spec["path"]:
    node[spec["path"][-1]] = spec["value"]
if spec["bad_tree"]:
    first = params["frozen_engine"]["checked_paths"][0]
    real = C.git
    C.git = lambda *a: "0" * 40 if a == ("rev-parse", f"HEAD:{first}") else real(*a)
try:
    if spec["runner"]:
        RN.frozen_check(params)
    else:
        C.engine_check(params, require_head_trees=spec["bad_tree"])
    print(json.dumps(None))
except (C.EngineMismatch, RN.RunnerRefused) as exc:
    print(json.dumps(str(exc.code)))
"""


@pytest.fixture(scope="module")
def p2_worktree(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """A worktree at the P2 commit holding what the P2 engine and manifest checks read."""
    _require_history()
    wt = tmp_path_factory.mktemp("p2") / "wt"
    paths = [
        ".gitignore",
        *PARAMS["frozen_engine"]["checked_paths"],
        "docs/verification/stage-04/evaluation-p2",
        *MF.EXTERNAL,
    ]
    _git("worktree", "add", "--no-checkout", "--detach", str(wt), P2_COMMIT)
    try:
        subprocess.run(["git", "reset", "-q"], cwd=wt, check=True)
        subprocess.run(["git", "checkout", "--", *paths], cwd=wt, check=True)
        yield wt
    finally:
        _git("worktree", "remove", "--force", str(wt))


def _historical(wt: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-I", "-B", "-c", HISTORICAL_PROBE]  # -B: no bytecode written into the checked tree
    return subprocess.run(cmd, cwd=wt, capture_output=True, text=True, check=False)


@pytest.mark.unit
def test_engine_check_accepts_the_frozen_freeze2_engine(p2_worktree: Path) -> None:
    """P2's engine check and runner guard, at the P2 commit, accept the freeze-2 engine there."""
    res = _historical(p2_worktree)
    assert res.returncode == 0, res.stderr[-2000:]
    out = json.loads(res.stdout)
    for check in ("engine_check", "frozen_check"):
        got = out[check]
        assert got["content_commit"] == FROZEN and got["tree"] == FROZEN_TREE, check
        assert got["freeze_manifest_digest"] == FREEZE_DIGEST, check
        assert got["identity"] == PARAMS["frozen_engine"]["identity"], check
        assert got["head"] == P2_COMMIT, check
    assert out["manifest_equal"] is True


def _mutated(path: tuple[str, ...], value: Any) -> dict[str, Any]:
    params = json.loads(json.dumps(PARAMS))
    node = params
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    return params


@pytest.mark.unit
@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("frozen_engine", "content_commit"), SUPERSEDED),
        (("frozen_engine", "tree"), "86152ad543971d321059f16f93c3aff671f467c4"),
        (
            ("frozen_engine", "freeze_manifest_digest"),
            "609796cee9fc168b379669dde7ca5c410868e37455944d86b12624578fae42cc",
        ),
        (("frozen_engine", "identity", "table_version"), "dt-1"),
        (("frozen_engine", "identity", "engine_version"), "0.2.0"),
        (("frozen_engine", "identity", "schema_version"), "3.0.0"),
        (("frozen_engine", "identity", "claim_schema_version"), "2.0.0"),
        (("frozen_engine", "identity", "detector_identity"), "citerift-dt1-detector/2"),
    ],
)
def test_engine_check_refuses_any_scientific_engine_mismatch(
    p2_worktree: Path, path: tuple[str, ...], value: str
) -> None:
    """Each mutation is refused by P2's own check at the P2 commit, where the unmutated parameters are accepted
    (reviewer finding D-04: in the dt-3 working tree every identity mutation was refused anyway)."""
    assert _mutation(p2_worktree, (), None) is None
    refused = _mutation(p2_worktree, path, value)
    assert refused is not None
    reason = {"content_commit": "frozen content commit", "tree": "tree", "freeze_manifest_digest": "manifest digest"}
    assert reason.get(path[-1], "running engine identity") in refused, refused


def _mutation(wt: Path, path: tuple[str, ...], value: Any, *, bad_tree: bool = False, runner: bool = False) -> Any:
    spec = json.dumps({"path": list(path), "value": value, "bad_tree": bad_tree, "runner": runner})
    res = subprocess.run(
        [sys.executable, "-I", "-B", "-c", MUTATION_PROBE, spec], cwd=wt, capture_output=True, text=True, check=False
    )
    assert res.returncode == 0, res.stderr[-2000:]
    return json.loads(res.stdout)


@pytest.mark.unit
def test_engine_check_refuses_a_different_committed_engine_tree(p2_worktree: Path) -> None:
    """At the P2 commit, a committed tree of a checked path that differs from the frozen one is refused (the
    ``differing`` branch; reviewer finding D-04)."""
    refused = _mutation(p2_worktree, (), None, bad_tree=True)
    assert refused is not None and "the engine is not the frozen one: differing ['" in refused, refused


@pytest.mark.unit
def test_engine_check_refuses_a_changed_engine_tree(p2_worktree: Path) -> None:
    """At the P2 commit, one uncommitted change to the engine makes P2's own check refuse it."""
    target = p2_worktree / "src/citerift/investigation/dt1.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n")
        res = _historical(p2_worktree)
    finally:
        target.write_bytes(original)
    assert res.returncode != 0
    assert "the engine is not the frozen one" in res.stderr


@pytest.mark.unit
def test_the_current_engine_is_not_the_freeze2_engine() -> None:
    """The working tree runs the dt-3 engine; P2's checks refuse it before anything runs."""
    with pytest.raises(C.EngineMismatch, match="identity"):
        C.engine_check(PARAMS)
    assert dt1.TABLE_VERSION == "dt-4" != PARAMS["frozen_engine"]["identity"]["table_version"]
    assert 'TABLE_VERSION = "dt-2"' in _git("show", f"{FROZEN}:src/citerift/investigation/dt1.py")


@pytest.mark.unit
def test_exposure_check_refuses_another_manifest() -> None:
    assert C.file_sha256(C.exposure_check(PARAMS)) == EXPOSURE_SHA
    old = _mutated(("exposure", "manifest_path"), "docs/verification/stage-04/freeze/exposure/EXPOSURE_MANIFEST.json")
    with pytest.raises(C.EngineMismatch):
        C.exposure_check(old)


# ------------------------------------------------------------------------------------------------ historical P


@pytest.mark.unit
def test_historical_p_and_campaign_are_unchanged() -> None:
    """D-076 section 1: P, its files at 827ac1a and the failed campaign at 1064113 are untouched by P2."""
    _require_history()
    assert C.digest(C.read_json(HISTORICAL / "PREREGISTRATION_MANIFEST.json")) == HISTORICAL_P
    assert _git("diff", "--name-only", PREREG_COMMIT, "HEAD", "--", "docs/verification/stage-04/evaluation") == ""
    campaign = "docs/verification/stage-04/evaluation-campaign"
    assert _git("diff", "--name-only", CAMPAIGN_COMMIT, "HEAD", "--", campaign) == ""
    assert HISTORICAL_PARAMS["frozen_engine"]["content_commit"] == SUPERSEDED


# ------------------------------------------------------------------------------------------------ frame


@pytest.fixture(scope="module")
def frame() -> dict[str, Any]:
    return C.read_json(P2 / "frame" / "FRAME.json")


@pytest.mark.unit
def test_frame_rebuilds_byte_for_byte(tmp_path: Path) -> None:
    out = tmp_path / "FRAME.json"
    assert FR.main(["--out", str(out)]) == 0
    assert out.read_bytes() == (P2 / "frame" / "FRAME.json").read_bytes()


@pytest.mark.unit
def test_frame_excludes_every_article_of_exposure_v2(frame: dict[str, Any]) -> None:
    """No-overlap proof, recomputed here independently of the frame tool's own check."""
    manifest = C.read_json(REPO / PARAMS["exposure"]["manifest_path"])
    assert frame["inputs"]["exposure_manifest_sha256"] == EXPOSURE_SHA
    exposed_ids = {(a["wiki"], int(a["page_id"])) for a in manifest["articles"] if a["page_id"] is not None}
    exposed_titles = {C.norm_title("en", t) for a in manifest["articles"] for t in a["titles"]}
    for wiki in C.LANGUAGES:
        for m in frame["frames"][wiki]["frame"]:
            assert (wiki, m["page_id"]) not in exposed_ids
            assert C.norm_title("en", C.norm_title(wiki, m["title"])) not in exposed_titles
    campaign = [a for a in manifest["articles"] if "S04-CAMPAIGN-80" in a["sources"]]
    assert len(campaign) == 80
    members = {(w, m["page_id"]) for w in C.LANGUAGES for m in frame["frames"][w]["frame"]}
    assert not {(a["wiki"], int(a["page_id"])) for a in campaign} & members
    assert frame["overlap_check"]["passed"] and frame["overlap_check"]["campaign_articles_in_frame"] == []


@pytest.mark.unit
def test_frame_counts_and_exclusion_audit(frame: dict[str, Any]) -> None:
    counts = {w: frame["frames"][w]["counts"] for w in C.LANGUAGES}
    assert counts["ar"]["frame_by_stratum"] == {"S1": 110, "S2": 29}
    assert counts["en"]["frame_by_stratum"] == {"S1": 346, "S2": 299}
    assert (counts["ar"]["excluded"], counts["en"]["excluded"]) == (56, 100)
    for wiki in C.LANGUAGES:
        for e in frame["frames"][wiki]["excluded"]:
            assert e["reasons"] and e["exposure_sources"], e
    campaign_excluded = sum(
        1 for w in C.LANGUAGES for e in frame["frames"][w]["excluded"] if "S04-CAMPAIGN-80" in e["exposure_sources"]
    )
    assert campaign_excluded > 0
    assert frame["exclude_listed_tier"] is False  # D-070: listed-only pages stay, marked
    assert counts["en"]["listed_only_kept"] == 412 and counts["ar"]["listed_only_kept"] == 7


@pytest.mark.unit
def test_capture_time_recheck_uses_exposure_v2() -> None:
    import p2_acquire as AQ

    excluded = AQ.exposure_check()
    manifest = C.read_json(REPO / PARAMS["exposure"]["manifest_path"])
    (jasist,) = [a for a in manifest["articles"] if a["key"] == "en:39868218"]
    assert excluded("en", 39868218, "anything") == ["exposure_page_id"]
    assert excluded("en", 1, jasist["titles"][0])  # moved page: caught by its title
    assert excluded("en", 1, "A page that no exposure source names") == []


# ------------------------------------------------------------------------------------------------ draw


@pytest.mark.unit
def test_p2_seed_and_order_tags_are_new() -> None:
    assert DR.SEED_TAG == "citerift-stage04-eval-seed/2" and DR.ORDER_TAG == "citerift-stage04-eval-order/2"
    assert not (P2 / "SEED.json").exists() and not (P2 / "DRAW.json").exists()


# ------------------------------------------------------------------------------------------------ packets, labels


def _records_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    header = ["Journal", "Author", "OriginalPaperDate", "RetractionDate", "ArticleType"]
    conn.executescript(
        "CREATE TABLE meta (key TEXT, value TEXT);"
        "CREATE TABLE event (ordinal INTEGER, event_id TEXT, record_id TEXT, event_type TEXT, title TEXT,"
        " original_doi TEXT, original_pmid TEXT, notice_doi TEXT, notice_pmid TEXT);"
        "CREATE TABLE raw_record (ordinal INTEGER, fields TEXT);"
    )
    conn.execute("INSERT INTO meta VALUES ('header', ?)", (json.dumps(header),))
    rows = [
        (1, "ev-1", "1", "retracted", "X causes Y", "10.1/a", None, "10.1/a", None),
        (2, "ev-2", "2", "retracted", "Z in mice", "10.2/b", "222", "10.2/notice", "222"),
        (3, "ev-3", "3", "correction", "W", "10.3/c", "333", "10.3/n", "334"),
    ]
    conn.executemany("INSERT INTO event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    conn.executemany(
        "INSERT INTO raw_record VALUES (?, ?)", [(i, json.dumps(["J", "A", "", "", ""])) for i in (1, 2, 3)]
    )
    return conn


@pytest.mark.unit
def test_packet_records_state_a_shared_work_and_notice_identifier() -> None:
    recs = PK.Records(_records_db())
    assert recs.record("ev-1")["same_identifier_for_work_and_notice"] == ["doi"]
    assert recs.record("ev-2")["same_identifier_for_work_and_notice"] == ["pmid"]
    assert recs.record("ev-3")["same_identifier_for_work_and_notice"] == []
    assert PK.FORMAT == "citerift-stage04-eval-packet/2"


@pytest.fixture(scope="module")
def index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw"))


@pytest.mark.integration
def test_packet_is_engine_independent(index: Path) -> None:
    packet, extraction = PK.packet(S8.EN_MMR, index)
    assert packet["extraction_digest"] == extraction["extraction_digest"]
    text = json.dumps(packet)
    for stage04 in ("RETRACTED_WORK_CITED", "IDENTIFIER_ROLE_COLLISION", "UNRESOLVED_IDENTITY", '"rule"', '"class"'):
        assert stage04 not in text
    assert packet["items"] and all(
        "same_identifier_for_work_and_notice" in r for it in packet["items"] for r in it["records"]
    )


def _label(iid: str, recs: dict[str, str], kind: str = "work_citation", same: str = "yes") -> dict[str, Any]:
    return {
        "item_id": iid,
        "kind": kind,
        "same_work": same,
        "records": recs,
        "single_identifier_attachable": "yes",
        "note": "",
    }


@pytest.mark.unit
def test_labels_accept_ambiguous_object_and_refuse_unknown_values() -> None:
    item = {"item_id": "i1", "records": [{"ref": "R1"}]}
    assert LB.label_problems(_label("i1", {"R1": "ambiguous_object"}), item) == []
    assert LB.label_problems(_label("i1", {"R1": "maybe"}), item)
    assert LB.FORMAT == "citerift-stage04-eval-labels/2"
    guide = (P2 / "ANNOTATION_GUIDE.md").read_text(encoding="utf-8")
    assert "`ambiguous_object`" in guide and "same_identifier_for_work_and_notice" in guide


# ------------------------------------------------------------------------------------------------ scorer


def _index_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE event (ordinal INTEGER, event_id TEXT);"
        "CREATE TABLE ident (ordinal INTEGER, scheme TEXT, norm TEXT, role TEXT);"
        "INSERT INTO event VALUES (1, 'ev-1'), (2, 'ev-2');"
        "INSERT INTO ident VALUES (1, 'doi', '10.1/work', 'original'), (1, 'doi', '10.1/work', 'notice'),"
        "(2, 'doi', '10.2/other', 'original'), (2, 'pmid', '222', 'original');"
    )
    return conn


def _item(uid: str) -> dict[str, Any]:
    return {
        "item_id": f"x-{uid}",
        "unit_id": uid,
        "records": [
            {"ref": "R1", "event_id": "ev-1", "reached_by": ["doi:10.1/work as original", "doi:10.1/work as notice"]},
            {"ref": "R2", "event_id": "ev-2", "reached_by": ["doi:10.2/other as original"]},
        ],
    }


WORK = [{"scheme": "doi", "normalized": "10.1/work"}]
OTHER = [{"scheme": "doi", "normalized": "10.2/other"}, {"scheme": "pmid", "normalized": "222"}]
COLLISION = {"class": "UNRESOLVED_IDENTITY", "reasons": ["IDENTIFIER_ROLE_COLLISION"]}


@pytest.mark.unit
def test_ambiguous_object_never_counts_as_a_correct_attachment() -> None:
    conn = _index_db()
    units = {"u1": [{"class": "RETRACTED_WORK_CITED", "keys": WORK}]}
    ok = SC.score_units(
        units, {"u1": _item("u1")}, {"u1": _label("x-u1", {"R1": "cited_work", "R2": "unrelated"})}, conn
    )
    assert ok["positive"][0]["correct"]
    amb = {"u1": _label("x-u1", {"R1": "ambiguous_object", "R2": "unrelated"})}
    out = SC.score_units(units, {"u1": _item("u1")}, amb, conn)
    assert not out["positive"][0]["correct"] and out["positive"][0]["ambiguous_object"]
    assert not SC.truth_positive(amb["u1"])


@pytest.mark.unit
def test_role_collision_abstentions_are_described_and_never_converted() -> None:
    conn = _index_db()
    units = {
        "u1": [{**COLLISION, "keys": WORK}],
        "u2": [{**COLLISION, "keys": WORK + OTHER}],
        "u3": [{**COLLISION, "keys": WORK}],
        "u4": [{"class": "UNRESOLVED_IDENTITY", "reasons": ["KEY_RESULTS_DIFFER"], "keys": WORK}],
    }
    items = {u: _item(u) for u in units}
    labels = {
        "u1": _label("x-u1", {"R1": "cited_notice", "R2": "unrelated"}, kind="notice_citation"),
        "u2": _label("x-u2", {"R1": "cited_work", "R2": "cited_work"}),
        "u4": _label("x-u4", {"R1": "cited_work", "R2": "unrelated"}),
    }
    out = SC.score_units(units, items, labels, conn)
    assert out["positive"] == []
    rows = {r["unit_id"]: r for r in out["role_collision"]}
    assert set(rows) == {"u1", "u2", "u3"}  # u4 is UNRESOLVED_IDENTITY for another reason
    assert not rows["u1"]["clean_cited_identifier_present"] and rows["u2"]["clean_cited_identifier_present"]
    assert not rows["u3"]["annotated"] and rows["u2"]["truth_positive"]
    summary = SC.role_collision_summary([dict(r, article="en-1") for r in out["role_collision"]])
    assert summary["units"] == 3 and summary["annotated"] == 2 and summary["unannotated"] == 1
    assert summary["notice_citation"]["x"] == 1 and summary["work_citation"]["x"] == 1
    assert summary["clean_cited_identifier_present"] == 1


@pytest.mark.unit
def test_clean_key_is_an_original_identifier_that_is_never_a_notice() -> None:
    conn = _index_db()
    assert SC.clean_key(conn, "doi", "10.2/other") and SC.clean_key(conn, "pmid", "222")
    assert not SC.clean_key(conn, "doi", "10.1/work")
    assert not SC.clean_key(conn, "doi", "10.9/absent")


@pytest.mark.unit
def test_withheld_truth_positives_are_counted_by_cause() -> None:
    assert SC.engine_cause([{**COLLISION, "keys": WORK}], None) == "role_collision"
    assert SC.engine_cause([{"class": "IDENTITY_CONFLICT", "reasons": [], "keys": WORK}], None) == "other_abstention"
    assert SC.engine_cause([{"class": "NOT_FOUND_IN_CHECKED_SOURCES", "reasons": [], "keys": WORK}], None) == (
        "other_class"
    )
    assert SC.engine_cause([], None) == "no_claim"
    assert SC.engine_cause([{"class": "RETRACTED_WORK_CITED", "keys": WORK}], False) == "positive_but_incorrect"


def _article(n_pos: int, n_false: int, n_neg: int, withheld: int = 0) -> dict[str, Any]:
    positive = [
        {
            "unit_id": f"p{i}",
            "classes": ["RETRACTED_WORK_CITED"],
            "correct": i >= n_false,
            "unannotated": False,
            "unverifiable": False,
            "ambiguous_object": False,
        }
        for i in range(n_pos)
    ]
    truth = [
        {"article": "en-1", "unit_id": f"p{i}", "identifier_reached": True, "engine_cause": "correct"}
        for i in range(n_false, n_pos)
    ] + [
        {"article": "en-1", "unit_id": f"w{i}", "identifier_reached": True, "engine_cause": "role_collision"}
        for i in range(withheld)
    ]
    negative = [{"unit_id": f"n{i}", "truth_positive": False} for i in range(n_neg)]
    engine = {"positive": positive, "negative": negative, "conflict": [], "hazards": [], "role_collision": []}
    return {"article": "en-1", "wiki": "en", "truth_positive_units": truth, "structural": [], "engine": engine}


@pytest.mark.unit
def test_gates_and_interval_are_the_historical_ones() -> None:
    params = {"gates": PARAMS["gates"]}
    s = SC.summarize([_article(30, 0, 60)], params)["en"]
    assert s["passed"] and abs(s["false_attachment_rate"]["one_sided_95_upper"] - 0.0950) < 1e-4
    assert not SC.summarize([_article(30, 1, 60)], params)["en"]["gates"]["G2_false_attachment_bound"]
    assert SC.summarize([_article(46, 1, 60)], params)["en"]["gates"]["G2_false_attachment_bound"]
    assert not SC.summarize([_article(45, 1, 60)], params)["en"]["gates"]["G2_false_attachment_bound"]
    assert not SC.summarize([_article(29, 0, 60)], params)["en"]["gates"]["G1_positive_denominator"]
    assert not SC.summarize([_article(30, 0, 59)], params)["en"]["gates"]["G5_negative_denominator"]


@pytest.mark.unit
def test_recall_counts_withheld_role_collision_truth_positives_separately() -> None:
    s = SC.summarize([_article(30, 0, 60, withheld=3)], {"gates": PARAMS["gates"]})["en"]
    assert s["truth_positive_units"] == 33 and s["recall_retrieval_scoped"]["x"] == 30
    assert s["truth_positive_withheld"]["role_collision"] == 3
    assert s["positive_units"] == 30  # a withheld truth positive is never an attachment


# ------------------------------------------------------------------------------------------------ corrected runner


@pytest.fixture(scope="module")
def run_index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return S8.build_index(tmp_path_factory.mktemp("rw-run"))


def _campaign(base: Path) -> Path:
    c = base / "campaign"
    shutil.copytree(S8.EN_MMR, c / "bundles" / NAME)
    return c


@pytest.mark.integration
def test_runner_defect_2_cannot_recur_the_first_article_exports(tmp_path: Path, run_index: Path) -> None:
    """Historical defect 2: no export parent, so the first article kept no export. P2 creates it first."""
    c = _campaign(tmp_path)
    assert not (c / "run" / "exports").exists()
    op = RN.prepare(c, tmp_path / "memory-outside")
    assert (c / "run" / "exports").is_dir()
    rec = RN.run_article(NAME, "en", c, run_index, Path(op["memory_root"]))
    assert rec["verify_passed"] is True
    assert rec["export"] == f"run/exports/{NAME}" and (c / rec["export"] / "export.json").is_file()
    assert "memory_root" not in rec


@pytest.mark.unit
@pytest.mark.parametrize("where", ["campaign", "repository", "working_tree", "relative"])
def test_runner_defect_1_cannot_recur_memory_inside_a_repository_is_refused(tmp_path: Path, where: str) -> None:
    """Historical defect 1: the memory root under the campaign, inside the repository. P2 refuses it before any
    article, and creates nothing there."""
    c = _campaign(tmp_path)
    roots = {
        "campaign": REPO / "docs/verification/stage-04/evaluation-p2/never-created/run/memory",
        "repository": REPO / "never-created-memory-root",
        "working_tree": tmp_path / "checkout" / "memory",
        "relative": Path("relative-memory"),
    }
    if where == "working_tree":
        (tmp_path / "checkout" / ".git").mkdir(parents=True)
    with pytest.raises(RN.RunnerRefused):
        RN.prepare(c, roots[where])
    assert not (REPO / "docs/verification/stage-04/evaluation-p2/never-created").exists()
    assert not (REPO / "never-created-memory-root").exists() and not Path("relative-memory").exists()


@pytest.mark.unit
def test_runner_refuses_an_existing_run(tmp_path: Path) -> None:
    c = tmp_path / "campaign"
    (c / "run").mkdir(parents=True)
    (c / "run" / "RUN.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RN.RunnerRefused, match=r"RUN\.json exists"):
        RN.main(["--campaign", str(c), "--index", str(tmp_path / "i.sqlite"), "--memory-root", str(tmp_path / "m")])
    assert not (tmp_path / "m").exists()


@pytest.mark.unit
def test_runner_refuses_another_engine_before_any_article(p2_worktree: Path) -> None:
    _require_history()
    # P2's runner guard at the P2 commit: the frozen engine is accepted there, each mutation refused (finding D-04).
    assert _mutation(p2_worktree, (), None, runner=True) is None
    assert _mutation(p2_worktree, ("frozen_engine", "content_commit"), SUPERSEDED, runner=True) is not None
    refused = _mutation(p2_worktree, ("frozen_engine", "identity", "table_version"), "dt-1", runner=True)
    assert refused is not None and "running engine identity" in refused
    with pytest.raises(RN.RunnerRefused):
        RN.frozen_check(PARAMS)  # the working tree is the dt-3 engine; the freeze-2 run guard refuses it
    with pytest.raises(RN.RunnerRefused, match="version"):
        RN.engine_identity("0.3.0")
    assert RN.engine_identity(__version__)["engine_version"] == __version__ == "0.5.0"


@pytest.mark.unit
def test_runner_refuses_another_preregistration(tmp_path: Path) -> None:
    c = tmp_path / "campaign"
    c.mkdir()
    C.write_json(c / "SEED.json", {"prereg_digest": HISTORICAL_P})
    C.write_json(c / "LOCK.json", {"packets": {}})
    # In the working tree this file differs from its P2 bytes, so the runner refuses before reading the seed.
    with pytest.raises(
        RN.RunnerRefused, match=r"pre-registered files changed: \['tests/stage04/test_p2_evaluation.py'\]"
    ):
        RN.prereg_check(c, RN.PREREG_MANIFEST)
    # The seed check itself, on a copy of the manifest naming this file's current bytes.
    manifest = C.read_json(RN.PREREG_MANIFEST)
    for f in manifest["files"]:
        if f["path"] == THIS_TEST:
            f["sha256"] = C.file_sha256(REPO / THIS_TEST)
    C.write_json(tmp_path / "manifest.json", manifest)
    with pytest.raises(RN.RunnerRefused, match="another pre-registration"):
        RN.prereg_check(c, tmp_path / "manifest.json")


# ------------------------------------------------------------------------------------------------ dev run, manifest


@pytest.mark.unit
def test_dev_run_ran_the_dt2_engine_with_the_committed_tools() -> None:
    dev = C.read_json(P2 / "dev" / "DEV_RUN.json")
    assert dev["engine_identity"]["identity"] == PARAMS["frozen_engine"]["identity"]
    assert dev["engine_identity"]["content_commit"] == FROZEN
    for name, sha in dev["tools"].items():
        assert C.file_sha256(TOOLS / name) == sha, name
    totals = dev["totals"]
    # P's 232 development revisions plus the 80 campaign articles that D-071/D-076 made design-exposed
    assert totals["revisions"] == 312 and totals["unfaithful"] == 0
    assert totals["self_checks_passed"] == 311 and totals["lifecycle"]["FAILED"] == 1
    assert {"a", "b", "c"} <= {k[-1] for k in totals if k.startswith("variant_")}
    historical = C.read_json(HISTORICAL / "dev" / "DEV_RUN.json")["revisions"]
    assert set(historical) <= set(dev["revisions"])
    assert dev["network_attempts"] == 0


@pytest.mark.unit
def test_p2_manifest_matches_the_files_and_names_the_identities() -> None:
    """The manifest in the tree is the one of the P2 commit, has digest P2, and every file it lists hashes, at the P2
    commit, to its recorded SHA-256; in the tree only this test file differs (its P2 bytes are proved here, and the
    manifest build at the P2 commit equals the record, see ``test_engine_check_accepts_the_frozen_freeze2_engine``)."""
    import hashlib

    _require_history()
    recorded = C.read_json(P2 / "PREREGISTRATION_MANIFEST.json")
    assert (REPO / MANIFEST_REL).read_text(encoding="utf-8") == _git("show", f"{P2_COMMIT}:{MANIFEST_REL}")
    assert C.digest(recorded) == P2_DIGEST
    for f in recorded["files"]:
        blob = subprocess.run(
            ["git", "show", f"{P2_COMMIT}:{f['path']}"], cwd=REPO, capture_output=True, check=True
        ).stdout
        assert hashlib.sha256(blob).hexdigest() == f["sha256"], f["path"]
    changed = sorted(f["path"] for f in recorded["files"] if C.file_sha256(REPO / f["path"]) != f["sha256"])
    assert changed == [THIS_TEST]
    assert recorded["frozen_engine"] == PARAMS["frozen_engine"]
    assert recorded["exposure"]["manifest_sha256"] == EXPOSURE_SHA
    assert recorded["historical_p"]["digest"] == HISTORICAL_P
    paths = {f["path"] for f in recorded["files"]}
    assert "tests/stage04/test_p2_evaluation.py" in paths
    assert "docs/verification/stage-04/evaluation-p2/PREREGISTRATION.md" in paths
    assert C.digest(recorded) != HISTORICAL_P
