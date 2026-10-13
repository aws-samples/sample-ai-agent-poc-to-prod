# Verification — Simplification Refactor

All commands run on Windows PowerShell in
`c:\Users\evaleah\amazon.com\AWE RTP - Documents\2026 All Things Open\poc-to-prod-demo`.
This is the FIRST iteration (no `simplify-review.json` existed), so the full
refactor from `simplify-plan.md` was performed.

---

## 1. Deterministic eval — no model, no network (HARD GATE)

Command:
```
python evaluation.py
```

Output:
```
PASS #1 layer_served: semantic layer served (catalog + join semantics)
PASS #2 sources_load: every known source loads with rows
PASS #3 s06_enriches: talk joined across tracks/rooms/speakers
PASS #4 s10_partial: missing room flagged TBD (partial), not invented
PASS #5 prompt_no_structure: system prompt carries no schedule structure
PASS #6 rejects_uncited: uncited answer rejected
PASS #7 rejects_hidden_partial: answer hiding S10's partial rejected
PASS #8 rejects_invented: invented room rejected
PASS #9 accepts_good: correct cited + TBD-flagged answer accepted
Score: 9/9 checks passed.
All eval checks passed.
EXITCODE=0
```

Exit code 0. The suite reduced from ten checks to nine: the version-sync check
(#10) was deleted together with `schema.json`. The five required invariant checks
are all present: layer served (#1), sources load (#2), S06 enrichment (#3), S10
TBD/partial (#4), no-structure-in-prompt (#5).

---

## 2. Imports with strands-agents UNINSTALLED (INV-6)

Confirm the SDK is absent:
```
python -c "import importlib.util as u; print('strands installed:', u.find_spec('strands') is not None)"
```
Output:
```
strands installed: False
```

Import every project module (incl. orchestration + agent that reference the SDK):
```
python -c "import data_platform, semantic, orchestration, agent, evaluation, main; print('all modules imported OK, no ImportError from missing SDK')"
```
Output:
```
all modules imported OK, no ImportError from missing SDK
```

No ImportError — the `try/except` `@tool` fallback holds and strands is only
imported lazily inside `build_agent`.

---

## 3. Beat-1 structure scan (unescaped-pipe PowerShell Select-String)

Positive control (should MATCH):
```
Select-String -Path semantic/joins.md -Pattern 'track_id|room_id|sessions'
```
Output:
```
semantic\joins.md:9:- sessions.track_id  -> tracks.track_id     (enrich a talk with its track name/theme)
semantic\joins.md:10:- sessions.room_id   -> rooms.room_id        (enrich a talk with room name/floor)
semantic\joins.md:11:- sessions.session_id -> speakers.session_id (attach the speaker(s) to a talk)
```

The proof — the agent SYSTEM_PROMPT file (should return NO matches):
```
Select-String -Path agent.py -Pattern 'track_id|room_id|sessions'
```
Output: (empty — no matches)

The positive control matches; the agent prompt file returns nothing.

---

## 4. `python main.py` fails gracefully (no stack dump) without strands/Bedrock

Command:
```
python main.py
```
Output:
```
Strands SDK not installed or model not configured.
Install with:  pip install strands-agents strands-agents-tools
Then set AWS_REGION + BEDROCK_MODEL_ID (see .env.example).
(import/runtime detail: No module named 'strands')
EXITCODE=0
```

Clean guidance, exit 0, no traceback.

---

## 5. File count dropped — final file list

~24 files across 6 packages collapsed to 6 flat Python modules + `semantic/`
(3 markdown) + `data/` (4 CSV).

Final tracked project files (excluding `.git`, `.agents`, `__pycache__`):
```
.env.example
.gitignore
agent.py
data_platform.py
DEMO_SCRIPT.md
evaluation.py
main.py
orchestration.py
README.md
requirements.txt
semantic.py
data\rooms.csv
data\sessions.csv
data\speakers.csv
data\tracks.csv
semantic\field_map.md
semantic\joins.md
semantic\sources.md
```

GONE (not dead files — removed from disk and staged in git):
`data_platform/`, `orchestration/`, `concierge/`, `observability/`,
`evaluation/` package dirs; `semantic/schema.json`, `semantic/layer.py`,
`semantic/__init__.py`; `eval_runner.py`.

---

## 6. Orphaned-import sweep

`grep` for dead names across `**/*.py` for
`DataPlatform|SemanticLayer|build_platform|register_connector|RunReport|observability|schema.json|concierge|SourceSpec|SourceError`
returned only benign prose matches: the product word "concierge", the word
"observability" in a comment, and "source catalog"/"schedule's structure" inside
the system prompt. No import statement or class reference to any deleted module
remains.

---

## 7. Cleanup

All `__pycache__` directories created during verification were removed.

---

## What was folded / deleted

- `data_platform/{types,connectors,catalog,platform,__init__}.py` → `data_platform.py`
  (plain `read_source`/`list_sources`; removed Connector Protocol, CsvConnector
  class, CONNECTORS registry, register_connector, Catalog, DataPlatform facade,
  SourceSpec/SourceError dataclasses).
- `semantic/layer.py` + `semantic/__init__.py` → root `semantic.py`
  (plain `read_semantic_layer`/`list_sources`; removed cached `SemanticLayer`
  class and all version plumbing). `semantic/schema.json` deleted; the source list
  is a 4-entry literal dict mirroring `sources.md`.
- `orchestration/{tools,enrichment,guardrails,__init__}.py` → `orchestration.py`
  (two @tools + `enrich_sessions` byte-for-byte join/TBD/partial behavior +
  inline guardrails). `observability.span(...)` replaced with a one-line timing
  print + OpenTelemetry comment.
- `concierge/{agent,config,__init__}.py` → `agent.py` (SYSTEM_PROMPT verbatim,
  `build_agent` default-provider path, ~10-line stdlib `.env` reader).
  `concierge/observability_report.py` (dead) deleted; cost theme is now two
  comments.
- `observability/` package deleted entirely.
- `evaluation/{contract_checks,scoring,model_in_the_loop,__init__}.py` +
  `eval_runner.py` → `evaluation.py` (nine deterministic checks + optional
  `--model` function + `__main__` runner). Check #10 (version sync) deleted.
- Docs: `README.md` rewritten for a newcomer (flat layout, read-order, five-theme
  bullets, threat model, disclaimer); `DEMO_SCRIPT.md` retargeted to the flat
  files and `python evaluation.py`; `.env.example` cost-rate lines removed.
