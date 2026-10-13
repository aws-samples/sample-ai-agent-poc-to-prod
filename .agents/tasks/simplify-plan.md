# Simplification Plan — Conference Schedule Concierge

Goal: collapse ~24 files across 6 packages into ~6 flat, heavily-commented modules
so a new programmer grasps the one idea in a few minutes:

> Move the knowledge of how your data fits together OUT of the LLM system prompt
> and INTO a governed, versioned data layer the agent reads at runtime. Build it
> once; add a track/room/source by editing the layer, not the code.

This plan is a REFACTOR. The current build is green (`python eval_runner.py` prints
all PASS). Behavior named in the invariants must be preserved byte-for-byte. We are
deleting indirection, not changing what the demo does.

Design decisions recorded inline (rationale in one or two sentences each) because
this plan deliberately OVERRIDES the "production-grade, maximally-layered" choice in
`.agents/tasks/design.md` in favor of readability.

---

## Target module list (what the project becomes)

Flat, at the project root, FOUR conceptual layers still map to the slide:

1. `data_platform.py`   — LAYER 1: reusable, domain-agnostic data foundation (one file).
2. `semantic/`          — LAYER 2: governed markdown (`sources.md`, `field_map.md`, `joins.md`) + one tiny reader `semantic.py` at root.
3. `orchestration.py`   — LAYER 3: the two Strands @tools + the deterministic join engine + inline guardrails.
4. `agent.py`           — LAYER 4: Strands Agent wiring + SYSTEM_PROMPT + tiny .env config.
5. `evaluation.py`      — deterministic checks + simple scoring, runnable as the one-command entry (`__main__`).
6. `main.py`            — thin CLI entry (kept, retargeted to `agent.py`).

Design decision — semantic reader placement: the three governed markdown files STAY
in `semantic/` (that folder IS the thesis and the demo opens it on stage). The tiny
reader becomes a flat `semantic.py` at the project root (plain functions, no class).
Rationale: keeps the governed content visually grouped as a folder while the code that
reads it is a flat, obvious module alongside its four siblings. A root `semantic.py`
module and a `semantic/` data folder coexist fine — Python imports the module file;
nothing imports the folder as a package once `semantic/__init__.py` is deleted.

Design decision — source list lives in `semantic.py` as a small literal dict with a
comment that it mirrors `sources.md`. Rationale: parsing the markdown table is extra
code that teaches nothing; a 4-entry literal dict is the clearest thing a reader can
see, and the dict-mirrors-markdown comment makes the governance point without a sync
guard. This replaces `schema.json` entirely (deleted — see invariant notes).

---

## (a) File-by-file mapping: every current file -> destination

### data_platform/ package -> `data_platform.py` (ONE file)
- `data_platform/types.py`       -> FOLDED. Drop `SourceSpec`/`SourceError` dataclasses and the `Mapping`/`options` machinery. Keep the idea of `Row = dict[str, str]` (a plain type alias or just an untyped list of dicts) and a plain "unknown source" error as a returned dict/`None`, not a frozen dataclass.
- `data_platform/connectors.py`  -> FOLDED, REDUCED. DELETE the `Connector` Protocol, `CsvConnector` class, `CONNECTORS` registry, and `register_connector`. Keep ONE plain function that reads a CSV with `csv.DictReader`. Keep the path-confinement check (resolve path, reject escape of the data root) as a few inline lines with a one-line security comment. Add the one-sentence comment: `# to add a non-CSV source you'd add a reader here`.
- `data_platform/catalog.py`     -> FOLDED. DELETE the `Catalog` class and `from_schema`. The source list becomes the small literal dict (mirrors `sources.md`) that `semantic.py` owns; `data_platform.py` receives it (or imports `list_sources()` from `semantic`).
- `data_platform/platform.py`    -> FOLDED. DELETE the `DataPlatform` facade class. Replace with plain functions: `list_sources()` (ids/paths, delegated to or re-exported from `semantic.py`) and `read_source(source_id)` -> list of row dicts (validates id against the known sources, reads the CSV, returns rows or an error dict). Keep it domain-agnostic: NO conference words (sessions/tracks/rooms/speakers) in any signature or docstring.
- `data_platform/__init__.py`    -> DELETED with the package. The `build_platform` integration helper is removed (callers call the plain functions directly).

Design decision — plain functions over a class: there is no state worth encapsulating
(reading a CSV is stateless). Module-level functions `list_sources()` /
`read_source(id)` are the smallest thing that still reads as "a reusable data
foundation." Rationale: the task asks for plain functions / one tiny class and no
SQLite-ready abstraction; functions win for readability here.

### semantic/ package -> `semantic/` (governed content) + `semantic.py` (reader)
- `semantic/sources.md`   -> KEPT, unchanged (governed, versioned; `# version: 0.2`).
- `semantic/field_map.md` -> KEPT, unchanged (`# version: 0.2`).
- `semantic/joins.md`     -> KEPT, unchanged (`# version: 0.2`; the only home of correlation logic).
- `semantic/schema.json`  -> **DELETED** (see invariant notes — replaced by the literal source dict in `semantic.py`).
- `semantic/layer.py`     -> FOLDED into root `semantic.py`. DELETE the cached `SemanticLayer` class and its memoization/`reload`/`schema`/`joins`/`version` methods. Replace with plain functions:
  - `read_semantic_layer()` -> the three markdown files joined with `"\n\n---\n\n"` (byte-for-byte the reference's `get_semantic_layer` body). No caching unless it is a trivial one-liner; prefer no caching for clarity.
  - `list_sources()` -> returns the small literal source dict/list (`{"sessions": "data/sessions.csv", ...}`) with a comment: `# mirrors the table in semantic/sources.md — add a row there and here to add a source`.
- `semantic/__init__.py`  -> DELETED with the package-as-code (the folder remains on disk as a data folder holding the three .md files; it is no longer a Python package).

Design decision — no `version()` / version plumbing survives: with `schema.json` gone
there is no second version source to reconcile, and the markdown `# version:` markers
remain as human-facing governance metadata. Nothing in code reads them. Rationale: the
version-sync machinery existed only to guard json-vs-markdown drift that we are
deleting; see invariant notes for the removed eval check.

### orchestration/ package -> `orchestration.py` (ONE file)
- `orchestration/tools.py`      -> FOLDED. Keep `get_semantic_layer()` and `query_source(source_id)` as the two Strands `@tool`s. KEEP the `try/except` import fallback that makes `@tool` a no-op when `strands` is absent (INV-6). DELETE the `observability.span(...)` wrapper calls (observability package is deleted). Replace with the simplest observability touch: an optional one-line timing log/print around the tool body (see Observability touch below).
- `orchestration/enrichment.py` -> FOLDED. Copy `enrich_sessions(...)` BYTE-FOR-BYTE in behavior (join keys, TBD strings, `partial` computation). Retarget its row reads to the new `data_platform.read_source(...)` plain function instead of a `DataPlatform` object. Signature may take no argument and call `read_source` directly, OR take the module's read function — pick the simplest; the join body is unchanged.
- `orchestration/guardrails.py` -> FOLDED, INLINE. Keep `validate_source_id(...)` (tool-boundary id check) and the three checker predicates `cites_sources`, `flags_partials`, `invents_nothing` plus the `_INVENTED_SENTINELS` tuple. Keep clear security comments ("treat tool output as data", "never invent / TBD"). These predicates are used by `evaluation.py`.
- `orchestration/__init__.py`   -> DELETED with the package.

Design decision — guardrail predicates live in `orchestration.py`, not `evaluation.py`.
Rationale: `validate_source_id` is a runtime tool-boundary guard used by `query_source`,
so it belongs with the tools; keeping the three answer-scoring predicates next to it
keeps all "security/guardrail" logic in one place the README threat-model paragraph can
point at. `evaluation.py` imports them. (Acceptable alternative: move the three scoring
predicates into `evaluation.py`. Chosen placement keeps orchestration.py as the single
"security lives here" file, matching the task's instruction to keep guardrails inline in
orchestration.)

### concierge/ package -> `agent.py` (ONE file)
- `concierge/agent.py`                 -> FOLDED. Keep `SYSTEM_PROMPT` (carries NO schedule structure — INV-3) and `build_agent(...)`. Keep the reference-style default-provider path (pass model id string, do not construct `BedrockModel`). Keep graceful-failure behavior.
- `concierge/config.py`                -> FOLDED. Keep the ~10-line stdlib `.env` reader and the model id/region settings. Drop the cost-rate fields and the `Settings` frozen dataclass if a couple of plain module functions/vars read more simply; a tiny dataclass or plain `load_config()` returning a small object/dict are both fine — pick the simpler. Keep `BEDROCK_MODEL_ID` + `AWS_REGION` from `.env` with the same defaults.
- `concierge/observability_report.py`  -> **DELETED** (dead run-level token/cost accounting; never wired into `main.py`). Its "cost" point survives as two commented lines in `agent.py` (model id is swappable; layer is read once). See invariant/theme notes.
- `concierge/__init__.py`              -> DELETED with the package.

Design decision — drop cost-rate config and the RunReport entirely. Rationale:
`observability_report.py`/`RunReport`/`build_report`/`set_enabled` are confirmed dead
(grep shows no caller in `main.py` or anywhere outside their own package). Keeping dead
indirection contradicts the simplification goal; the cost theme is better served by two
comments than by unused token-accounting code.

### observability/ package -> **DELETED ENTIRELY**
- `observability/tracing.py`  -> DELETED. The whole package (a stdlib timing context manager + enable flag + span counter) collapses to one optional timing line in `orchestration.py` with the comment `# in production this is where OpenTelemetry spans go`.
- `observability/__init__.py` -> DELETED.

### evaluation/ package -> `evaluation.py` (ONE file) + runner folded in
- `evaluation/contract_checks.py`   -> FOLDED. Keep checks #1–#4 (layer served, sources loadable, S06 enrichment joins, S10 partial/TBD). **DELETE check #10** `test_version_consistent` and the `_VERSION_RE`/markdown-version plumbing (schema.json is gone).
- `evaluation/scoring.py`           -> FOLDED. Keep check #5 (`test_prompt_carries_no_structure`, the INV-3 whole-word scan with the `FORBIDDEN` list) and the four scoring checks #6–#9 (reject uncited / hidden-partial / invented; accept good). May be renumbered/renamed for clarity, but each must still run.
- `evaluation/model_in_the_loop.py` -> FOLDED as a short, clearly-labeled OPTIONAL function at the bottom of `evaluation.py` (behind the `--model` flag), OR documented as a README snippet. Keep it never-required and model/network only behind the flag.
- `evaluation/__init__.py`          -> DELETED with the package.
- `eval_runner.py` (root)           -> FOLDED into `evaluation.py`'s `if __name__ == "__main__":` block with the `--model` argparse flag. The one-command entry becomes `python evaluation.py`. (DEMO_SCRIPT/README must be updated to the new command — see docs.)

Design decision — fold the runner into `evaluation.py __main__` rather than keep a
separate `eval_runner.py`. Rationale: one fewer file, and a reader opening
`evaluation.py` sees the checks and how they run in one place. Update all doc references
from `python eval_runner.py` to `python evaluation.py`.

### Root files
- `main.py`           -> KEPT, retargeted import from `concierge.agent` to `agent` (root module). Keep the graceful SDK-missing message.
- `data/*.csv`        -> KEPT unchanged (sessions/tracks/speakers/rooms). The S10 `room_id='Main'` gap and the A/B/C/D-only rooms STAY.
- `requirements.txt`  -> KEPT unchanged (`strands-agents==1.58.1`, `strands-agents-tools==0.8.9`).
- `.env.example`      -> KEEP `AWS_REGION` + `BEDROCK_MODEL_ID`. Remove the two cost-rate lines (`INPUT_COST_PER_1K` / `OUTPUT_COST_PER_1K`) since cost accounting is deleted.
- `.gitignore`        -> KEPT (optionally drop `build.log` line; harmless either way).
- `README.md`         -> REWRITTEN (see docs section).
- `DEMO_SCRIPT.md`    -> UPDATED (see docs section).
- `.agents/tasks/*`   -> KEPT on disk (internal), but ALL user-facing references to `design.md`/`requirements.md`/`.agents/` must be removed from README and DEMO_SCRIPT.

---

## (b) Explicit DELETE list (must not be left as dead files)

Delete these files and the two package directories outright:

Files:
- `semantic/schema.json`
- `semantic/layer.py`
- `semantic/__init__.py`
- `orchestration/tools.py`
- `orchestration/enrichment.py`
- `orchestration/guardrails.py`
- `orchestration/__init__.py`
- `concierge/agent.py`
- `concierge/config.py`
- `concierge/observability_report.py`
- `concierge/__init__.py`
- `data_platform/types.py`
- `data_platform/connectors.py`
- `data_platform/catalog.py`
- `data_platform/platform.py`
- `data_platform/__init__.py`
- `observability/tracing.py`
- `observability/__init__.py`
- `evaluation/contract_checks.py`
- `evaluation/scoring.py`
- `evaluation/model_in_the_loop.py`
- `evaluation/__init__.py`
- `eval_runner.py`

Directories removed as a result (must end empty/gone):
- `data_platform/`  (becomes the file `data_platform.py` at root — NOT a dir)
- `orchestration/`  (becomes `orchestration.py`)
- `concierge/`      (becomes `agent.py`)
- `observability/`  (deleted, no replacement)
- `evaluation/`     (becomes `evaluation.py`)

Directory KEPT (as a data folder, not a package):
- `semantic/`  — retains `sources.md`, `field_map.md`, `joins.md` only.

Use `git rm` (or delete then `git add -A`) so the removals are staged; do not leave
empty `__pycache__` or orphan dirs. Verify with `git status` that no stray files from
the old packages remain.

---

## (c) Behavior that MUST be copied byte-for-byte

1. **`enrich_sessions` join logic** — the dict comprehension bodies and output dict:
   - `tracks = {r["track_id"]: r ...}`, `rooms = {r["room_id"]: r ...}`,
     `speakers_by_session` keyed by `session_id` appending `speaker_name`.
   - Output keys: `session_id, title, day, start, end, track_name, room_name, speakers, partial`.
   - TBD strings EXACTLY: `f"TBD (track '{s['track_id']}' missing)"` and
     `f"TBD (room '{s['room_id']}' missing)"`; speakers default `["TBD"]`.
   - `partial = not (track and room)`.
   Only the data-access call changes (`platform.read_rows(sid)` -> `read_source(sid)`);
   the join/TBD/partial semantics are unchanged.
2. **The three join keys** — `sessions.track_id -> tracks.track_id`,
   `sessions.room_id -> rooms.room_id`, `sessions.session_id -> speakers.session_id`.
   Keep them in `joins.md` (unchanged) and in the enrichment code.
3. **TBD / partial-result behavior** — S10 (`room_id='Main'`, absent from `rooms.csv`)
   must still produce `room_name` starting with `TBD` and `partial=True`.
4. **The `try/except strands import` @tool fallback** — copy the reference form:
   ```python
   try:
       from strands import tool
   except Exception:
       def tool(fn=None, **_):
           return (lambda f: f) if fn is None else fn
   ```
   so `orchestration.py` and `agent.py` import with strands UNINSTALLED (INV-6).
5. **`SYSTEM_PROMPT`** — carry it over verbatim from `concierge/agent.py` (it already
   passes the no-structure scan; do not reintroduce the reference's `(track_id, room_id,
   session_id)` parenthetical).
6. **The `FORBIDDEN` token list + whole-word `\b` scan** in check #5 — copy exactly
   (`sessions, tracks, speakers, rooms, track_id, room_id, session_id`, matched
   case-insensitively as `\b`-bounded whole words over the lowercased prompt).
7. **The guardrail predicates and `_INVENTED_SENTINELS`** — copy `cites_sources`,
   `flags_partials`, `invents_nothing`, and the sentinel tuple
   (`grand ballroom, keynote hall, quantum computing, jane fictional`) verbatim.

---

## (d) Reduced eval check set (what each check verifies)

Keep FIVE checks (down from ten). Drop #10 entirely. Each must run with NO model and
NO network, importing only stdlib + the new project modules.

1. **layer served** — `read_semantic_layer()` text contains `"Source Catalog"`,
   `"Join Semantics"`, and `"session_id"`. (ports contract #1)
2. **sources load** — for every id in `list_sources()`, `read_source(id)` returns a
   non-empty list of rows (not an error). (ports contract #2)
3. **S06 enrichment joins** — `enrich_sessions()[S06]` has `track_name == "AI & Agents"`,
   `room_name == "Workshop Room C"`, `"Sam Okoye" in speakers`, `partial is False`.
   (ports contract #3 — INV-4)
4. **S10 flagged TBD/partial** — `enrich_sessions()[S10]` has `partial is True` and
   `room_name` contains `"TBD"`. (ports contract #4 — INV-1)
5. **no structure in the prompt** — the `\b`-bounded whole-word scan finds none of the
   `FORBIDDEN` tokens in `agent.SYSTEM_PROMPT`. (ports check #5 — INV-3)

Scoring predicates (#6–#9 behavior) may be kept as part of check 5's neighborhood or as
additional small checks that exercise `cites_sources` / `flags_partials` /
`invents_nothing` against the enrichment output + fixed synthetic candidate strings.
Keeping them is encouraged (they are the "catch hallucinations early" theme) but the
MINIMUM required set is the five above. Whatever set ships, the suite must still:
assert a perfect score and print a final "All eval checks passed." line, and
`python evaluation.py` must exit 0.

**DELETED check:** #10 `test_version_consistent` (markdown-vs-json version sync) —
removed together with `schema.json` and the `SemanticLayer.version()` plumbing. No
replacement; there is no second version source to reconcile.

Optional `--model` path: a short labeled function at the bottom of `evaluation.py`
(folded from `model_in_the_loop.py`) that builds a live agent, asks the demo question,
and scores the answer with the same three predicates. Never required; only runs behind
`python evaluation.py --model`.

---

## (e) Orphaned-import cleanup

After the moves, no file may import from the deleted packages. Specifically remove or
rewrite every import of:
- `from data_platform import ...` / `from data_platform.types import ...` /
  `from data_platform.X import ...`  -> use the new `data_platform.py` plain functions.
- `from semantic import SemanticLayer` / `from semantic.layer import ...` ->
  `import semantic` / `from semantic import read_semantic_layer, list_sources`.
- `from orchestration.enrichment import enrich_sessions` /
  `from orchestration.tools import ...` / `from orchestration.guardrails import ...` ->
  `from orchestration import enrich_sessions, cites_sources, ...`.
- `from observability import span` (and `span_count`, `set_enabled`, etc.) -> REMOVE;
  replace span usage with the inline timing line.
- `from concierge.agent import build_agent, SYSTEM_PROMPT` / `from concierge.config import Settings`
  -> `from agent import build_agent, SYSTEM_PROMPT` (and config folded into `agent.py`).
- In `main.py`: `from concierge.agent import build_agent` -> `from agent import build_agent`.
- In `evaluation.py`: drop the `sys.path.insert` / `pathlib` runner glue only if no
  longer needed (root-level modules import directly); keep whatever makes
  `python evaluation.py` run from the project dir.

Verification that nothing dangles: after the refactor, grep the tree for the dead
package names and confirm zero hits in `.py` files:
`data_platform/`, `semantic.layer`, `orchestration.`, `observability`, `concierge`,
`SemanticLayer`, `DataPlatform`, `build_platform`, `register_connector`, `RunReport`,
`schema.json`. (Grep is a cleanup aid here, NOT the acceptance test — the eval is.)

---

## Docs the plan must cover

### README.md (rewrite for a newcomer)
- Open with the one idea: knowledge of how data fits together lives in the governed
  semantic layer, not the prompt; build once, add a source by editing the layer.
- ASCII architecture diagram of the FOUR simplified layers (data_platform -> semantic
  -> orchestration -> agent) with an explicit arrow/callout: *"knowledge lives in the
  semantic layer, not the prompt."*
- "Read the code in this order" section pointing at the ~6 files:
  `data_platform.py` -> `semantic/` + `semantic.py` -> `orchestration.py` ->
  `agent.py` -> `evaluation.py` -> `main.py`.
- The five themes as SHORT bullets ("here's where each idea lives"):
  evaluation (`evaluation.py`), observability (the one timing line in `orchestration.py`),
  cost (swappable model id + layer read once), security (inline guardrails + threat-model
  paragraph), modularity (edit the markdown + CSV, not the code).
- Keep a short threat-model paragraph (prompt injection: tool output is data;
  data leakage: id validated against known sources, path confined to the data root,
  two read-only tools).
- Keep setup / usage / eval instructions. Eval command becomes `python evaluation.py`.
- Keep the educational / synthetic-data / fictional-conference disclaimer.
- Style: state what IS needed directly (avoid "X not required, but..." framing).
  Framework-neutral tone (Strands is the concrete SDK; the pattern is model/framework
  -agnostic).
- Remove references to `.agents/`, `design.md`, `requirements.md`, the per-package
  docstrings, `schema.json`, and the "why packages, not flat" section (now obsolete).

### DEMO_SCRIPT.md (update to the new flat layout)
- Keep beats 0–4, the S10 "room TBD" moment, and the hand-off lines.
- Beat 0: the "tree is the diagram" line now points at the ~6 flat files, not six
  packages.
- Beat 1: keep the "prove no structure in the prompt" scan. Update the scanned path
  from `concierge/agent.py` to `agent.py`, and the positive-control path stays
  `semantic/joins.md`. KEEP the unescaped-pipe form of the regex and the escaping note.
- Beat 2: open `semantic/*.md`. REMOVE the `semantic/schema.json` "machine mirror"
  line (schema.json is deleted); if desired, point instead at the small source dict in
  `semantic.py` as the machine-readable mirror of `sources.md`.
- Beat 3: `python main.py "..."` is unchanged.
- Beat 4: the add-a-track flow (edit `data/tracks.csv` + `data/sessions.csv`, re-run)
  is unchanged and should be MORE obviously code-free now. If `list_sources()` holds a
  literal dict, adding a brand-new *source* also needs a one-line dict edit — but
  adding a track/room/session (Beat 4) is pure data edit, no code; keep Beat 4 as a
  data-only edit.
- Fallback: `python eval_runner.py` -> `python evaluation.py`. Update the "ten checks"
  wording to the reduced count.
- Remove any `.agents/`-internal references.

### requirements.txt — unchanged (`strands-agents==1.58.1`, `strands-agents-tools==0.8.9`).

---

## Ordered implementation steps

Each step leaves the tree in a known state; the final gate is the eval. Because this is
a cross-cutting collapse, the modules are built bottom-up so each new module's
dependencies already exist before the module that imports them.

- [ ] 1. Create `data_platform.py` at the project root — fold `types.py` +
      `connectors.py` + `catalog.py` + `platform.py` into plain functions:
      `read_source(source_id)` (validate id against known sources, read CSV via
      `csv.DictReader`, path-confine to the data root, return rows or an error dict) and
      a `Row` alias. Domain-agnostic signatures (no conference words). Add the
      `# to add a non-CSV source you'd add a reader here` comment. Do NOT yet delete the
      old `data_platform/` package (keep the tree importable mid-refactor).
      Files: `data_platform.py` (new).
      Verify: `python -c "import data_platform"` — fails here because the package dir
      shadows the module; so instead defer verification to step 8 after the package dir
      is deleted. For now: `python -c "import ast; ast.parse(open('data_platform.py').read())"`
      parses with no SyntaxError.

- [ ] 2. Create root `semantic.py` — fold `semantic/layer.py` into plain functions
      `read_semantic_layer()` (join the three .md with `"\n\n---\n\n"`) and
      `list_sources()` (literal dict mirroring `sources.md`, with the mirror comment).
      Files: `semantic.py` (new). Keep `semantic/*.md` untouched.
      Verify: `python -c "import ast; ast.parse(open('semantic.py').read())"` parses.
      (Full import verified at step 8, once `semantic/__init__.py` is gone so the
      module name no longer collides with the package.)

- [ ] 3. Create `orchestration.py` at the project root — fold `tools.py` +
      `enrichment.py` + `guardrails.py`. Copy `enrich_sessions` byte-for-byte (retarget
      row reads to `read_source`), the two `@tool`s with the try/except strands
      fallback, the inline `validate_source_id`, and the three scoring predicates +
      `_INVENTED_SENTINELS`. Replace `observability.span(...)` with one optional timing
      line + the OpenTelemetry comment.
      Files: `orchestration.py` (new).
      Verify: `python -c "import ast; ast.parse(open('orchestration.py').read())"` parses.

- [ ] 4. Create `agent.py` at the project root — fold `concierge/agent.py` +
      `concierge/config.py`. Carry `SYSTEM_PROMPT` verbatim, keep `build_agent(...)` on
      the default-provider path, fold in the ~10-line `.env` reader + model id/region.
      Add two comment lines for the cost theme (swappable model id; layer read once).
      Files: `agent.py` (new).
      Verify: `python -c "import ast; ast.parse(open('agent.py').read())"` parses.

- [ ] 5. Create `evaluation.py` at the project root — fold `contract_checks.py` (#1–#4,
      DROP #10) + `scoring.py` (#5 + #6–#9) + the optional `model_in_the_loop` as a
      bottom `--model` function, and fold the `eval_runner.py` CLI into
      `if __name__ == "__main__":` with the `--model` argparse flag. Import enrichment
      and predicates from `orchestration`, layer readers from `semantic`, sources from
      `data_platform`/`semantic`. End with the perfect-score assert + "All eval checks
      passed." print.
      Files: `evaluation.py` (new).
      Verify: `python -c "import ast; ast.parse(open('evaluation.py').read())"` parses.

- [ ] 6. Retarget `main.py` — change `from concierge.agent import build_agent` to
      `from agent import build_agent`. Keep the graceful SDK-missing message.
      Files: `main.py`.
      Verify: `python -c "import ast; ast.parse(open('main.py').read())"` parses.

- [ ] 7. Delete the old packages and `schema.json` / `eval_runner.py` (full list in
      section (b)). Use `git rm -r data_platform orchestration concierge observability
      evaluation` for the code packages, `git rm semantic/layer.py semantic/__init__.py
      semantic/schema.json eval_runner.py`, leaving `semantic/*.md` in place.
      Files: all files in section (b).
      Verify: `git status` shows the deletions staged and `semantic/` still holds only
      the three `.md` files; no leftover `__init__.py` / `.pyc` from the old packages.

- [ ] 8. Run the eval end-to-end — the acceptance gate.
      Files: none.
      Verify: `python evaluation.py` prints PASS for all five (or more) checks and ends
      with "All eval checks passed.", exit code 0. Also confirm INV-6:
      `python -c "import orchestration, agent, data_platform, semantic, evaluation"`
      succeeds with strands UNINSTALLED (the try/except fallback holds).

- [ ] 9. Orphaned-import sweep — grep the tree for dead names (section (e) list) and
      confirm zero hits in `.py` files; fix any stragglers, re-run step 8.
      Files: any with dangling imports.
      Verify: grep returns no matches for `DataPlatform`, `SemanticLayer`,
      `build_platform`, `register_connector`, `RunReport`, `observability`,
      `schema.json`, `concierge`, `orchestration.`, `data_platform.` (dotted submodule
      forms); `python evaluation.py` still green.

- [ ] 10. Rewrite README.md and update DEMO_SCRIPT.md and `.env.example` per the docs
      section. Update the eval command to `python evaluation.py`, the file-order
      reading list to the ~6 flat modules, remove `schema.json` / `.agents` / per-package
      references, and keep the disclaimer, threat model, and the five-theme bullets.
      Files: `README.md`, `DEMO_SCRIPT.md`, `.env.example`.
      Verify: re-read both docs — every path/command names a file that now exists
      (`agent.py`, `evaluation.py`, `semantic/*.md`); no reference to a deleted file
      (`eval_runner.py`, `schema.json`, `concierge/`, `observability/`). Re-run
      `python evaluation.py` to confirm nothing in the docs edit touched code.

- [ ] 11. Manual spot-check of the Beat-1 scan on the new path (DEMO_SCRIPT correctness):
      run the structure scan against `agent.py` and `semantic/joins.md`.
      Files: none.
      Verify (PowerShell): `Select-String -Path agent.py -Pattern 'track_id|room_id|sessions'`
      prints nothing (the proof); `Select-String -Path semantic/joins.md -Pattern 'track_id|room_id|sessions'`
      prints matches (the positive control).

---

## Invariant checklist (all 7 preserved)

1. S10 `room_id='Main'` + rooms A/B/C/D only -> "room TBD" partial. KEPT (data unchanged; eval check 4).
2. Three join keys unchanged in `joins.md` + `enrich_sessions`. KEPT (byte-for-byte).
3. No schedule structure in `SYSTEM_PROMPT`; eval check 5 proves it. KEPT.
4. S06 -> 'AI & Agents', 'Workshop Room C', 'Sam Okoye', partial=False. KEPT (eval check 3).
5. Deterministic eval runs with no model / no network, stdlib + project only; model
   only behind `--model`. KEPT.
6. Imports + eval run with strands UNINSTALLED (try/except @tool fallback). KEPT (step 8 verify).
7. Beat 4 "add a track by editing markdown + CSV, re-run, it appears" with no code
   change. KEPT and made more obvious.

Removed deliberately: `schema.json`, the `SemanticLayer` version plumbing, eval check
#10 (version sync), the `observability/` package, `concierge/observability_report.py`
(dead), the Connector/registry/SQLite abstraction, the cost-rate config.
