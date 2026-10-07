# Design Review — Conference Schedule Concierge (poc-to-prod-demo)

**Reviewed:** `.agents/tasks/design.md`
**Against:** `.agents/tasks/requirements.md` and the reference implementation at
`ATO2026_Working_Materials/semantic-layer-agent`
**Verdict:** CHANGES_REQUESTED (1 MEDIUM, several NITs)

This is a third-pass review. The design has already absorbed two prior review
rounds (11 findings, then 4 findings) and documents those resolutions in §13. I
reviewed the document fresh — reading the actual reference source and data to
verify every load-bearing claim rather than trusting the design's own §13.2
"verified" list. Most of the design is strong, specified to the code level, and
its hardest claims (the escaped-pipe Beat-1 bug fix, the whole-word prompt scan,
the non-uniform version-line parse, the S10 gap, the three join keys, the S06/S05
anchors) are all verified correct below. One theme (Observability, Theme B) has an
implementability gap in its only concrete code surface; that is the single
blocking finding.

---

## Findings

### 1. MEDIUM — Theme B observability hook has no concrete injection point in the one `tools.py` listing

**Where:** §7B ("Hooks are injected via a lightweight wrapper around tool calls in
`orchestration/tools.py` that is a no-op when observability is disabled") vs. the
concrete `tools.py` code block in §4.1.

**Problem:** Theme B is a first-class requirement (FR-6.1, Acceptance Criterion 10):
emit per-step structured traces including latency, which tools were called, and
token/step counts. The design names the mechanism — a wrapper around tool calls —
but the only concrete `orchestration/tools.py` listing (§4.1) shows the two tools
as bare module-level `@tool` functions with no wrapper, no span, and no timing. The
tools are what the Strands agent invokes directly, so "which tools were called" and
per-tool `latency_ms` (the §7B `tool_call` and `step` events) have to be captured
*at* those call sites. Nothing in the specified code shows how the wrapper obtains
the tool name, the arg summary, and the duration without altering the `@tool`
functions the agent is handed — and §4.1 explicitly hands the un-wrapped
`get_semantic_layer`/`query_source` to `build_agent` (§4.2). As written, an
implementer cannot tell whether to (a) wrap each `@tool` body in a `span(...)`
context manager, (b) register a Strands callback/hook, or (c) decorate the tools
with an observability decorator layered under `@tool`. These produce materially
different code and different "no-op when disabled" plumbing. Every other theme has
a concrete code home with a shown signature; Theme B's per-step capture does not.

**Concrete fix:** Add a short code block to §7B (or §4.1) that shows the actual
wrapper. The lightest form that satisfies FR-6.1 without touching the agent-facing
signatures is an in-body span keyed off an observability flag, e.g.:

```python
# orchestration/tools.py
from concierge.observability import span, is_enabled   # no-op span when disabled

@tool
def query_source(source_id: str) -> list[dict]:
    """..."""
    with span("tool.query_source", source_id=source_id):   # no-op when disabled
        err = validate_source_id(source_id, _PLATFORM.list_source_ids())
        if err:
            return [err]
        rows = _PLATFORM.read_rows(source_id)
        from data_platform.types import SourceError
        return [{"error": rows.error}] if isinstance(rows, SourceError) else rows
```

Specify that `span(name, **fields)` is a `contextlib.contextmanager` in
`observability.py` that, when enabled, records `start`/`end`/`duration_ms` and emits
one JSON log line, and when disabled yields immediately (a true no-op, preserving
the no-network eval property per FR-6.4). State where "token/step counts" come from
(the Strands result usage metadata read once in the run summary, which §7B already
says — but tie the per-*step* `step_count` to the number of `tool.*` spans emitted so
Acceptance Criterion 10's "token/step counts" is actually produced). This keeps the
`@tool` functions importable with Strands uninstalled (INV-9) because `span`/
`is_enabled` are stdlib-only. Importantly, note that `orchestration` importing from
`concierge.observability` creates an orchestration→concierge dependency that
contradicts the §1 "dependencies point downward only: application → orchestration"
rule — so either put the `span`/no-op primitive in a layer orchestration may depend
on (e.g. a small `observability` core under `orchestration/` or a shared module) or
explicitly amend the dependency-direction statement. Resolve that direction before
build; as written §7B's wrapper location (`orchestration/tools.py` calling into
`concierge/observability.py`) silently inverts the §1 architecture claim, which is
the architecture-diagram slide (NFR-5).

---

### 2. NIT — `scoring.py` check #1 (`test_layer_served`) is attributed to `scoring.py` in §5A but is listed as a `contract_checks` floor check in §6

**Where:** §5A lists `test_layer_served` as the first *contract floor* check in
`contract_checks.py`; §6's table row #1 ("Layer served…") is labeled "reference
floor"; but §3.1 says `scoring.py::test_prompt_carries_no_structure` and §5A lists
`test_prompt_carries_no_structure` under *scoring* as added check #5. The split of
which checks live in `contract_checks.py` vs `scoring.py` is mostly clear, but the
"check number" scheme in §6 (1–10) does not map one-to-one to the §5A function names
(contract 1–4, scoring 5–9, version 10), and §6 check #5 ("System prompt contains no
source ids…") is the same thing as §5A's scoring check #5
`test_prompt_carries_no_structure`. This is internally consistent on close reading
but easy to misimplement as two separate prompt checks.

**Concrete fix:** In §6's table, add the owning module + function name to each row
(e.g. row 5 → `scoring.test_prompt_carries_no_structure`; row 10 →
`contract_checks.test_version_consistent`) so the ten numbered checks map
unambiguously to the nine named functions plus the version check. No logic change.

---

### 3. NIT — eval `quality_score` for the drift record (FR-6.2) is computed over fixed synthetic answers, not a model answer, which the design does not state plainly

**Where:** §7B ("The eval writes the same `{layer_version, quality_score}` record so
CI history is comparable") and Theme B drift mapping.

**Problem (minor):** In the deterministic eval there is no agent answer — the
scoring predicates run over the fixed synthetic candidate answers from §5A. So the
`quality_score` the eval records per layer version is a constant for a given set of
synthetic answers + a given layer version; it only moves when the layer version or
the synthetic fixtures change. That is adequate for FR-6.2 ("associate a quality
signal with the layer version" so drift *across versions* can be shown), but a reader
could expect the eval's quality_score to reflect live model quality. It does not, by
design and correctly (NFR-2 determinism).

**Concrete fix:** One sentence in §7B: "In the deterministic eval the `quality_score`
is computed over the fixed synthetic answers, so it is stable per `{layer_version}`
and changes only when the layer version or fixtures change; live model quality is
recorded only on the optional `--model` path." This prevents an implementer from
wiring a model call into the deterministic record and breaking INV-4.

---

### 4. NIT — Beat 4 "no reload needed" claim is correct for data-only edits but the `sources.md`/`schema.json` add-a-source path does need a reload

**Where:** §5E Beat-4 ("call `_LAYER.reload()` is unnecessary for data-only edits
(platform re-reads files each `query_source`)") and §9 Beat 4 row.

**Problem (minor):** The claim is true for the *demo's* Beat 4 as scripted (paste a
`tracks.csv` row + a `sessions.csv` row — pure data edits; `query_source` re-reads
the CSV each call, and `enrich_sessions` re-reads too, so new rows appear with no
reload). But the design elsewhere (§5E first bullet, Acceptance Criterion 5, FR-1.2)
describes the stronger extensibility proof: adding a *new source* by editing
`sources.md` + `schema.json`. That path *does* require `_LAYER.reload()` within a
running process, because `_PLATFORM` is built once from the cached
`SemanticLayer.schema()` at module import (§4.1) and the catalog will not see the new
source id until the schema cache is invalidated. The design never says this, and the
cached `_PLATFORM`/`_LAYER` being module-level means a live "add a new source" in the
same process silently won't take effect without `reload()` + rebuilding `_PLATFORM`.

**Concrete fix:** Clarify in §5E: "A data-only edit (new row in an existing CSV) needs
no reload — `query_source`/`enrich_sessions` re-read the file each call. Adding a *new
source* (new `schema.json`/`sources.md` entry) requires `_LAYER.reload()` **and**
rebuilding `_PLATFORM` from the refreshed schema, since the catalog is built once at
import; in practice this means restarting the process (the demo's Beat 4 avoids this
by staying data-only, and the extensibility *test* in §11 builds a fresh platform per
run)." This keeps Acceptance Criterion 5 honest (it is verified by the §11 test which
builds a fresh platform, not by an in-process live edit).

---

## Verified Assumptions (checked against reference source/data, not taken on trust)

1. **S10 "Main" gap (INV-1).** VERIFIED. `data/sessions.csv` S10 "Panel: The Future
   of Open Source" has `room_id=Main`, `track_id=community`, `day=Tue`. `data/rooms.csv`
   contains only A/B/C/D — "Main" is absent. The design preserves this verbatim (§8) and
   the enrichment flows it through to `partial=True` + TBD room (§3.3, eval check #4). Correct.

2. **Three join keys (INV-2).** VERIFIED. `semantic_layer/joins.md` and the data confirm
   `sessions.track_id→tracks.track_id`, `sessions.room_id→rooms.room_id`,
   `sessions.session_id→speakers.session_id`. Design §8/schema.json `joins` array matches exactly.

3. **S06 fact anchors (FR-10.3, eval check #3).** VERIFIED. S06 "Production-Grade Agent
   Architectures": `track_id=ai` → "AI & Agents" (tracks.csv), `room_id=C` → "Workshop Room C"
   (rooms.csv), speaker "Sam Okoye" (speakers.csv S06), day Tue. `partial=False`. All design
   claims (§8, §5A check 3) match.

4. **S05 / "two AI talks Tuesday, both Workshop Room C, Sam Okoye" narration.** VERIFIED.
   S05 "Building AI Agents 101" is also `track_id=ai`, `room_id=C`, `day=Tue`, speaker "Sam
   Okoye". The design's §8/§9 narration claim holds against the data.

5. **Served-text headers (eval check #1).** VERIFIED. `sources.md` has "# Source Catalog",
   `joins.md` has "# Join Semantics", and `session_id` appears in `joins.md`. The reference
   `get_semantic_layer` joins the three files; design §2.6 `served_text()` reproduces that join
   byte-for-byte, so `test_layer_served` will pass.

6. **Non-uniform `# version:` lines (design §2.6 / review finding 13.1#3).** VERIFIED. In the
   reference, `sources.md` carries `# version: 0.1  (add a source by adding a row here — no agent
   code changes)` with trailing prose, while `joins.md` and `field_map.md` carry a clean
   `# version: 0.1`. The design's regex rule `#\s*version:\s*(\S+)` (capture group 1) correctly
   extracts `0.1`/`0.2` from all three and ignores the prose. The naive split the design forbids
   would indeed fail. Correct and well-specified.

7. **Beat-1 structure-scan pipe (review findings 13.1#1/#2).** VERIFIED by execution. In
   PowerShell `Select-String`, an **unescaped** `track_id|room_id|sessions` matches via
   alternation; an **escaped** `track_id\|room_id\|sessions` does not match (treated as a literal).
   The design's fix (unescaped pipe + positive-control run against `joins.md`) is correct for both
   `Select-String` (.NET regex) and `grep -iE` (POSIX ERE).

8. **§4.2 prompt passes the whole-word forbidden-token scan (INV-3, §3.1).** VERIFIED by
   execution. The §4.2 prompt contains none of `sessions / tracks / speakers / rooms /
   track_id / room_id / session_id` as `\b`-bounded whole words. Dropping the reference prompt's
   `(track_id, room_id, session_id)` parenthetical is what makes this pass; the design flags that
   deviation. Correct.

9. **SDK-optional `tool` fallback (INV-9, FR-3.5).** VERIFIED. The reference `semantic_tool.py`
   uses the exact `try: from strands import tool / except Exception: def tool(...)` fallback the
   design reproduces in §4.1. Tools import without Strands; the deterministic eval path is stdlib-only.

10. **Reference `enrich_sessions()` is parameterless (module-global reads); design parameterizes
    it with `DataPlatform` (§3.3/§11).** VERIFIED. The reference reads via bare `query_source()`
    over a module-global `_CATALOG`. The design's single structural change (take a `DataPlatform`
    arg, call `platform.read_rows`) preserves the join keys and `partial`/TBD semantics byte-for-byte;
    the §8 "byte-for-byte" wording is correctly scoped to semantics, not the signature (NIT 13.1#8).

11. **Reference `query_source` error shape `[{"error": ...}]` (FR-1.5, AC13).** VERIFIED. The
    reference returns `[{"error": f"unknown source_id ..."}]`; design §4.1 preserves this at the tool
    boundary while the platform returns a structured `SourceError` object — the §5A/§6 check #2
    wording was correctly fixed (13.1#4) to say "not a `SourceError`" at platform level.

12. **Single-command eval on Windows PowerShell (FR-5.5, §6).** VERIFIED plausible. The
    `cd "<quoted path with spaces>"` then `python eval_runner.py` primary form, and the backslash-quoted
    absolute-path form, are both valid PowerShell. The project path contains spaces and is correctly
    quoted. `eval_runner.py` inserting its own dir on `sys.path` matches the reference pattern and runs
    from any cwd. The dependency set for the eval (stdlib + project modules) runs with no pip install
    (NFR-4) — confirmed the four contract checks and scoring predicates need no third-party package.

13. **Default question preserved (FR-4.1).** VERIFIED. "What AI talks are on Tuesday, who is speaking,
    and in which room?" matches the reference `main.py` default and DEMO_SCRIPT Beat 3.

14. **Demo beats 0–4 + TBD moment + eval fallback (INV-6, FR-11.3).** VERIFIED against the reference
    DEMO_SCRIPT. The §9 remap preserves the beats and narration, repoints paths to the layered tree, and
    keeps `python eval_runner.py` as the no-network fallback. The "Where is the Future of Open Source
    panel?" TBD question (S10) is preserved.

---

## Unverified / Wrong Assumptions

These are items the design relies on that could NOT be verified in this environment.
The design already flags all four and places each on a non-fatal / build-verify path,
so none is a blocking finding — but they are recorded here so the implementer treats
them as verify-before-ship, not settled.

1. **`strands.models.BedrockModel` constructor signature (`region` vs `region_name`,
   `model_id`).** UNVERIFIED — `strands-agents` is not installed in this environment, so the
   signature cannot be read from resolved source. The design correctly moves the required/demo path
   to the reference-style default provider (model id from config, no explicit `BedrockModel`), leaving
   the explicit `BedrockModel` as a documented alternative the planner must verify against the installed
   package before use (§1, §4.2). Acceptable.

2. **Strands agent result `token_usage` metadata path (FR-7.4, Theme C/B).** UNVERIFIED. The design
   reads usage "when present, else `None`," so a missing/renamed field degrades to no cost estimate
   rather than an error (§7B). Non-fatal. The implementer must confirm the actual attribute path on the
   installed SDK's result object before claiming live token/cost numbers on stage.

3. **Default Bedrock model id `us.anthropic.claude-3-5-haiku-20241022-v1:0`.** UNVERIFIED — Bedrock
   inference-profile ids drift by region prefix and version suffix, and no Bedrock catalog is reachable
   here. The design marks it a build-time placeholder to confirm against the team's enabled account/region
   (§7.1, `.env.example`); if unverified the model path is treated as unconfigured and the CLI fails
   gracefully (FR-4.4) while the no-model eval still passes. Acceptable, but NFR-6 (demo faithfulness)
   depends on it being set correctly before the talk.

4. **`requirements.txt` pins `strands-agents==1.10.0`, `strands-agents-tools==0.2.9`.** UNVERIFIED —
   no package index reachable here. The design states these are latest-known-good to be re-pinned at build
   time (§7.2). Acceptable.

---

## Verdict rationale

HIGH findings: 0. MEDIUM findings: 1 (Finding 1 — Theme B observability hook has no
concrete injection point and its stated location inverts the §1 downward-only
dependency rule). NITs: 3. Per the mechanical rule, one MEDIUM ⇒ **CHANGES_REQUESTED**.

The design is close. Finding 1 is a genuine implementability gap in a required theme
(per-step observability is Acceptance Criterion 10) and additionally conflicts with the
architecture-diagram dependency direction (NFR-5), so it must be resolved — not
downgraded — before the design is build-ready. The three NITs are clarity fixes that
would prevent predictable misimplementation. Everything else, including the hardest
previously-contested claims, is verified correct against the reference source and data.
