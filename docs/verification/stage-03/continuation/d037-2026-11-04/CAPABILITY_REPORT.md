# D-037 evaluator capability report

CITERIFT — Created and Directed by EVE TELOS · IM

Executor: OpenAI Codex. Date: 2026-11-04. Starting revision:
`7646fe77a3190f46c332f6c5ee3d176f6f48cc4c`.

**SCIENTIFIC_CONTINUATION_BLOCKED_BY_INDEPENDENT_EVALUATOR_RUNTIME**

The owner has authorized OpenAI substitution. The remaining blocker is an
auditable independent execution environment, not missing methodological authority.
No scientific evaluator/adjudicator received a packet. No label, lock, prediction
or score was produced. These were article-free capability probes.

## Hosted context probe

The executor used the advertised collaboration interface:

```json
{"task_name":"isolation_capability_probe","fork_turns":"none","model":"gpt-6.1-sol","reasoning_effort":"high"}
```

The only task message asked whether the probe received earlier task/project
messages, could observe its serving model/snapshot, could export its native
complete transcript, and could restrict all tools to an external directory. It
explicitly forbade file/repository reads and research, annotation or evaluation.
No packet, guide, decision, failure result or implementing detail was supplied.
It returned as `/root/isolation_capability_probe`.

The following is its **handback**, retained as a self-report, not a substitute
for the unavailable native session transcript:

> 1. **Prior context:** I received one earlier user message containing environment context (`/workspace`, Bash, date/timezone, and filesystem permissions). I received general system/developer instructions and tool/skill catalogs. I received no earlier substantive user task or project-specific instructions.
>
> 2. **Model identity:** A developer instruction describes me as “Codex, an agent based on GPT-6.” That is an instructed identity, not verified runtime metadata. No exact serving model identifier, requested model override, immutable snapshot, or version is exposed to me.
>
> 3. **Native transcript export:** I inspected the available tool metadata. No supported tool for exporting my complete native raw session transcript, including all incoming messages and tool calls, was exposed. I cannot establish whether the host has an unexposed export facility.
>
> 4. **Permission narrowing:** No exposed tool can enforce restriction of my entire session to one external working directory while removing repository and network access. `exec_command.workdir` selects a working directory; its permission arguments can request additional access, and do not expose a way to revoke baseline access. Behavioral restraint would not establish enforced isolation.
>
> I used only in-memory tool metadata inspection. I performed no shell commands, file/repository reads, research, annotation, evaluation, or external service calls.

The parent can establish that `fork_turns: none` was requested and that this
handback was returned. It cannot certify a native all-message/tool transcript
from that handback. The parent inspected the exposed tools and likewise found
no complete-session export or per-child permission-revocation control. A common
workspace and global tool access remain available; selecting a workdir is not
an access restriction. A fresh context alone does not satisfy all the owner's
requirements. The probe was not promoted into an evaluator.

## Native runtime probe

The installed CLI reports `codex-cli 0.166.0-alpha.1`. The supported local
`codex app-server proxy` route could not connect to
`/home/agent/.codex/app-server-control/app-server-control.sock`, including a retry
with normal socket permissions. No messages from other sessions were requested.
No local sessions directory exists at `/home/agent/.codex/sessions` in this
workspace. No credential file was inspected.

The executor then invoked a fresh native CLI in an external, packet-free
directory, using the existing configured authentication:

```sh
timeout 35s codex --no-daemon exec --ephemeral --skip-git-repo-check \
  -C /workspace/d037-capability/probe -m gpt-6.1-sol --json \
  'Capability probe only. Do not use tools or read files. Reply with CAPABILITY_PROBE_OK.'
```

Native stdout/stderr are retained byte-for-byte as `native-cli-probe.jsonl` and
`native-cli-probe.stderr.txt`. The native event stream records thread
`01a1a7e4-3638-7071-b375-72409d58ac25`, turn started, authentication error, turn
failed. Process exit was 1, before timeout. No completion was returned. The
native error says the access token cannot be refreshed because the session was
logged out or signed into another account. Stderr records HTTP 401 during model
catalog/response access and HTTP 451 from an MCP transport. These are observed
errors, not evidence of the underlying account state or of a serving model
snapshot. No article was sent. No login, token replacement, new paid API,
alternative account or route was attempted.

Runtime status reports no configured secrets, runtime variables or outbound
identities, with observations current. This does not imply that the hosted
agent tools or GitHub transport lack their own managed authorization. It does
not supply native CLI authentication. General HTTP policy is enforced and
unrestricted; the observed native inference failure is not repaired by a
scientific amendment.

## Original evaluator and checkpoint

The original reserve1 directory under `/tmp/claude-0/-home-user-citerift/`
is absent; `/home/user/citerift` and `/mnt/project-files` are unavailable here.
No Claude CLI or Claude evaluator tool is exposed. Whether the original host
holds reserve1 outputs is unknown. The seven initial raw transcripts and
private reviewer worktrees/exports remain unavailable; their committed audits,
labels and existing evidence remain untouched.

`preflight-integrity.json` revalidates the frozen candidate and 29 file/protocol
digests, 40 locked labels, 44 packets/captures, 238 content-addressed artifacts,
revision pins and reserve1 assignment. Its inventory pins the unchanged D-036
directory. All 35 earlier checkpoint checksum entries still pass. The prior
checkpoint CI is now completed/success at its exact SHA (see
`prior-checkpoint-ci.json`); no older result is attributed to a newer revision.
Completed 2,051-test matrices and engineering evidence were read and preserved,
not rerun to duplicate the prior work.

## Disposition

The executor records D-037 prospectively and registers B-03-001 with the existing
governance tool. The next scientific step remains the four English reserve1
annotations, followed by format-only validation and a committed lock. The
model-substitution authorization is not rescinded or treated as missing.

The minimum unblock is a supported authenticated evaluator runtime that can
provide all of: fresh contexts receiving only authorized inputs; restricted
tool/file/network access; actual model/version metadata; native complete-session
export; and durable byte-exact outputs/timestamps. Alternatively recover valid
original Claude work and contexts. Do not use a self-written log to impersonate
a raw transcript, accept unaudited labels, add a paid API, or weaken the model,
independence or provenance standard merely to advance the experiment.

No scientific failure is observed, and G6b/G6c have not failed. Stage 03 remains
`IMPLEMENTED_NOT_VERIFIED`. The clean integration branch is conditional on actual
scientific success and was not created. No original branch/PR was changed and
nothing was merged.

BLOCKED — EVIDENCE PROVIDED
