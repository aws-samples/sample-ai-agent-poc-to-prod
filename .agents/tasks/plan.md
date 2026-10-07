# Implementation Plan — Conference Schedule Concierge (poc-to-prod-demo)

Build the layered demo exactly to `.agents/tasks/design.md` (sections 1–13) and `.agents/tasks/requirements.md`. All files go at the top level of the project directory and in the packages named in design §1. The project directory IS the step cwd / workspace root:

```
c:\Users\evaleah\amazon.com\AWE RTP - Documents\2026 All Things Open\poc-to-prod-demo
```

Build order follows the dependency graph (design §12): observability leaf → data_platform → semantic → orchestration → concierge → evaluation → docs/dotfiles. Each item leaves the tree buildable/importable.

## Carried-over artifacts and their source paths (reference)

Reference root: `C:\Users\evaleah\amazon.com\AWE RTP - Documents\2026 All Things Open\ATO2026_Working_Materials_2026-10-07_v1\ATO2026_Working_Materials\semantic-layer-agent`

| New file | Source in reference | How carried over |
|----------|---------------------|------------------|
| `data/sessions.csv` | `data/sessions.csv` | verbatim — KEEP S10 `room_id=Main` |
| `data/tracks.csv` | `data/tracks.csv` | verbatim |
| `data/speakers.csv` | `data/speakers.csv` | verbatim |
| `data/rooms.csv` | `data/rooms.csv` | verbatim — rooms A/B/C/D only, NO "Main" |
| `semantic/sources.md` | `semantic_layer/sources.md` | near-verbatim, `# version:` bumped to `0.2` (keep trailing prose on this line) |
| `semantic/field_map.md` | `semantic_layer/field_map.md` | near-verbatim, `# version: 0.2` |
| `semantic/joins.md` | `semantic_layer/joins.md` | near-verbatim, `# version: 0.2`, keep three keys + correctness rules |
| `orchestration/enrichment.py` | `semantic_tool.py::enrich_sessions` | ported to take `DataPlatform` arg (design §3.3) |
| `orchestration/tools.py` | `semantic_tool.py` (`get_semantic_layer`, `query_source`, SDK-optional `tool` fallback) | design §4.1 |
| `evaluation/contract_checks.py` | `eval/test_cases.py` (4 floor checks) | re-pointed at `enrich_sessions(platform)` |
| `DEMO_SCRIPT.md` | `DEMO_SCRIPT.md` | beats 0–4 narration verbatim, paths remapped per design §9 |
| `README.md` | `README.md` | adapted to layered layout + 5 themes + threat model |
| `.env.example` | `.env.example` | expanded per design §7.3 |
| `.gitignore` | `.gitignore` | verbatim (design §7.4) |

## Confirmed data invariants (verified against reference during planning)
- S10 "Panel: The Future of Open Source" → `track_id=community, room_id=Main, day=Tue, 15:00–15:45`. "Main" is absent from `rooms.csv` (A=Hall A, B=Hall B, C=Workshop Room C, D=Workshop Room D). KEEP.
- S06 "Production-Grade Agent Architectures" → `track_id=ai` (→ "AI & Agents"), `room_id=C` (→ "Workshop Room C"), `session_id=S06` speaker "Sam Okoye", `partial=False`.
- S05 "Building AI Agents 101" → `track_id=ai, room_id=C, day=Tue`, speaker "Sam Okoye" — the second AI/Tuesday talk the narration cites.
- Three join keys: `sessions.track_id→tracks.track_id`, `sessions.room_id→rooms.room_id`, `sessions.session_id→speakers.session_id`.

## Pinned dependencies (verified current on PyPI during planning)
`requirements.txt`:
```
strands-agents==1.58.1
strands-agents-tools==0.8.9
```
Rationale: these are the latest released versions on PyPI (strands-agents 1.58.1 published 2026-10-06; strands-agents-tools 0.8.9 published 2026-09-15). The design's `1.10.0`/`0.2.9` were explicitly placeholder pins to update at build time (design §7.2). Everything else is stdlib — no other deps. The deterministic eval never imports these.

## Where each of the 8 KEY INVARIANTS is enforced
1. **S10 Main gap** — `data/sessions.csv` (S10 keeps `room_id=Main`) + `data/rooms.csv` (no "Main"); flows through `enrichment.py` (`rooms.get("Main")` is None → `partial=True`, TBD room). Checked by eval #4.
2. **Three join keys** — documented only in `semantic/joins.md` + `semantic/schema.json["joins"]`; applied only in `orchestration/enrichment.py`.
3. **No schedule structure in system prompt** — `concierge/agent.py` `SYSTEM_PROMPT` (design §4.2 exact text). Enforced by eval #5 (`scoring.py::test_prompt_carries_no_structure`), `\b`-whole-word scan of FORBIDDEN = [sessions, tracks, speakers, rooms, track_id, room_id, session_id], case-insensitive.
4. **Deterministic eval, no model/no network** — `eval_runner.py` runs `contract_checks.run_all()` + `scoring.run_all()`; imports only stdlib + project modules. `--model` is the ONLY model/network path.
5. **Importable without Strands** — `orchestration/tools.py` try/except `tool` decorator fallback (design §4.1); `observability/tracing.py` is stdlib-only so the import chain holds.
6. **span() true no-op when disabled** — `observability/tracing.py`; eval never calls `set_enabled(True)`/`configure_logging()`.
7. **DEMO_SCRIPT beats 0–4** — `DEMO_SCRIPT.md` remapped per design §9, incl. Beat 4 data-only add-a-track flow and S10 TBD moment.
8. **S06 anchor + S05 narration** — `data/*.csv`; checked by eval #3.

## Ordered build items

- [ ] 1. Create the observability leaf package `observability/` with `tracing.py` (stdlib-only `span(name, **fields)` contextmanager, `is_enabled`, `set_enabled`, `span_count`, `configure_logging`, env `OBSERVABILITY` flag) and `__init__.py` re-exporting them with the design §1 docstring. Code is design §4.1 verbatim.
      Files: `observability/__init__.py`, `observability/tracing.py`
      Verify: `python -c "import observability as o; o.set_enabled(False); c=o.span; __import__('contextlib');
      from observability import span; 
      exec('from observability import span\nwith span(\"t\"): pass\nprint(\"ok\")')"` → prints `ok`; and with it disabled no output is logged.

- [ ] 2. Create `data/` CSVs by copying the four reference CSVs verbatim (sessions, tracks, speakers, rooms). Preserve S10 `room_id=Main` and rooms A/B/C/D only.
      Files: `data/sessions.csv`, `data/tracks.csv`, `data/speakers.csv`, `data/rooms.csv`
      Verify: `python -c "import csv; r=list(csv.DictReader(open('data/rooms.csv'))); assert 'Main' not in [x['room_id'] for x in r]; s=list(csv.DictReader(open('data/sessions.csv'))); assert [x for x in s if x['session_id']=='S10'][0]['room_id']=='Main'; print('ok')"` → `ok`.

- [ ] 3. Create `data_platform/` package: `types.py` (Row, SourceSpec, SourceError), `connectors.py` (Connector protocol, CsvConnector with path confinement, CONNECTORS registry, register_connector), `catalog.py` (Catalog + from_schema), `platform.py` (DataPlatform: list_sources, list_source_ids, get_source, read_rows), `__init__.py` (re-exports + build_platform). Code is design §2.1–2.5 verbatim.
      Files: `data_platform/{__init__,types,connectors,catalog,platform}.py`
      Verify: `python -c "from data_platform import build_platform; p=build_platform([{'id':'rooms','location':'data/rooms.csv'}], __import__('pathlib').Path('.')); rows=p.read_rows('rooms'); assert isinstance(rows,list) and rows; err=p.read_rows('nope'); print(type(err).__name__)"` → prints `SourceError`.

- [ ] 4. Create `semantic/` package: carry over `sources.md`/`field_map.md`/`joins.md` (bump versions to 0.2), add `schema.json` (design §8 exact JSON, version "0.2"), add `layer.py` (SemanticLayer: served_text, schema, joins, version, reload — design §2.6 verbatim) and `__init__.py` re-exporting SemanticLayer with the design §1 docstring.
      Files: `semantic/{sources.md,field_map.md,joins.md,schema.json,layer.py,__init__.py}`
      Verify: `python -c "from semantic import SemanticLayer; from pathlib import Path; L=SemanticLayer(Path('semantic')); assert 'Source Catalog' in L.served_text() and 'Join Semantics' in L.served_text(); assert L.version()=='0.2'; assert any(s['id']=='rooms' for s in L.schema()); print('ok')"` → `ok`.

- [ ] 5. Create `orchestration/` package: `enrichment.py` (`enrich_sessions(platform)` ported per §3.3), `guardrails.py` (`validate_source_id`, `cites_sources`, `flags_partials`, `invents_nothing` per §3.2/§3.4), `tools.py` (`get_semantic_layer`, `query_source` with SDK-optional `tool` fallback, module-level `_LAYER`/`_PLATFORM`, span-wrapped bodies per §4.1), `__init__.py` with design §1 docstring.
      Files: `orchestration/{__init__,enrichment,guardrails,tools}.py`
      Verify: `python -c "from orchestration.enrichment import enrich_sessions; from data_platform import build_platform; from semantic import SemanticLayer; from pathlib import Path; p=build_platform(SemanticLayer(Path('semantic')).schema(), Path('.')); rows={r['session_id']:r for r in enrich_sessions(p)}; assert rows['S06']['room_name']=='Workshop Room C' and rows['S06']['partial'] is False; assert rows['S10']['partial'] is True and 'TBD' in rows['S10']['room_name']; print('ok')"` → `ok`.

- [ ] 6. Create `concierge/` package: `config.py` (Settings + _load_env, §7.1; default `BEDROCK_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0`, region us-east-1), `agent.py` (SYSTEM_PROMPT exact §4.2 text, `build_agent`, `_build_model` string/default-provider path), `observability_report.py` (run-level token/cost + drift record, §7B), `__init__.py` docstring. `service.py` is OPTIONAL — skip unless time allows.
      Files: `concierge/{__init__,config,agent,observability_report}.py`
      Verify: `python -c "from concierge.agent import SYSTEM_PROMPT; import re; FORBIDDEN=['sessions','tracks','speakers','rooms','track_id','room_id','session_id']; low=SYSTEM_PROMPT.lower(); bad=[t for t in FORBIDDEN if re.search(r'\\b'+re.escape(t)+r'\\b', low)]; assert not bad, bad; print('clean')"` → `clean`. Also `python -c "from concierge.config import Settings; s=Settings.from_env(); print(s.model_id, s.region)"` works.

- [ ] 7. Create `main.py` (CLI entry: default question verbatim "What AI talks are on Tuesday, who is speaking, and in which room?", graceful import/config failure per §4.2/FR-4.4, delegates to concierge).
      Files: `main.py`
      Verify: `python -c "import ast; ast.parse(open('main.py').read()); print('syntax ok')"` → `syntax ok`. (No Bedrock call; graceful-failure path prints install guidance when strands absent.)

- [ ] 8. Create `evaluation/` package: `contract_checks.py` (checks #1–4 re-pointed at `enrich_sessions(platform)` + #10 version-consistency with regex `#\s*version:\s*(\S+)`), `scoring.py` (checks #5–9 using guardrails predicates + the prompt structure scan), `model_in_the_loop.py` (OPTIONAL, behind `--model`), `__init__.py`. Each module exposes `run_all()`. Code mirrors design §5A/§6.
      Files: `evaluation/{__init__,contract_checks,scoring,model_in_the_loop}.py`
      Verify: covered by item 9.

- [ ] 9. Create `eval_runner.py` at project root (design §6: inserts own dir on sys.path, argparse `--model`, runs `contract_checks.run_all()` then `scoring.run_all()`, prints "All eval checks passed.").
      Files: `eval_runner.py`
      Verify (both documented forms, design §6):
      (a) `cd "c:\Users\evaleah\amazon.com\AWE RTP - Documents\2026 All Things Open\poc-to-prod-demo"; python eval_runner.py`
      (b) `python "c:\Users\evaleah\amazon.com\AWE RTP - Documents\2026 All Things Open\poc-to-prod-demo\eval_runner.py"`
      Both print all ten checks PASS and `All eval checks passed.` with exit code 0, NO network/model.

- [ ] 10. Create `requirements.txt` (pins above), `.env.example` (§7.3), `.gitignore` (§7.4).
      Files: `requirements.txt`, `.env.example`, `.gitignore`
      Verify: `python -c "assert '==' in open('requirements.txt').read(); print('ok')"` → `ok`.

- [ ] 11. Create `README.md` (layered architecture + ASCII/mermaid diagram, 5 themes mapped to code locations, reusable-data-platform story, threat model for prompt injection + data leakage, setup/usage, eval instructions, disclaimer; no "X not required, but…" framing) and `DEMO_SCRIPT.md` (beats 0–4 remapped per design §9, incl. exact Beat-1 structure-scan commands with UNESCAPED pipe for both PowerShell and grep, and S10 TBD + Beat-4 data-only payoff).
      Files: `README.md`, `DEMO_SCRIPT.md`
      Verify: `python -c "t=open('DEMO_SCRIPT.md').read(); assert 'track_id|room_id|sessions' in t; print('ok')"` → `ok` (unescaped-pipe pattern present).

## Final verification commands (run after all items)
1. **Deterministic eval, primary form:** `cd "<project>"; python eval_runner.py` → all 10 checks PASS, exit 0.
2. **Deterministic eval, absolute-path form:** `python "<project>\eval_runner.py"` → same.
3. **Strands-uninstalled import smoke test:** in an env with no `strands` installed, `python -c "import orchestration.tools, orchestration.enrichment, evaluation.contract_checks, evaluation.scoring; print('import ok')"` → `import ok` (proves INV-9 / FR-3.5). If strands IS installed in the build env, temporarily shadow it: run with a sitecustomize or `python -c "import sys; sys.modules['strands']=None; ..."` to force the except branch, OR assert the fallback `tool` is defined.
4. **Beat-1 structure-scan positive control + proof (PowerShell):**
   `Select-String -Path semantic/joins.md -Pattern 'track_id|room_id|sessions'` → MATCHES (positive control);
   `Select-String -Path concierge/agent.py -Pattern 'track_id|room_id|sessions'` → NO output (proof). Record both outputs.
5. **main.py graceful-failure syntax check:** `python -c "import ast; ast.parse(open('main.py').read()); print('syntax ok')"` → `syntax ok`.

## Notes / assumptions
- Model id `us.anthropic.claude-3-5-haiku-20241022-v1:0` is the design default placeholder; it is only on the live `--model`/CLI path and is not required for the floor. Left as-is per design §7.1 (verify against enabled Bedrock region before a live demo).
- `_build_model` uses the string/default-provider path (design §4.2, Finding #6); do NOT construct `BedrockModel` unless its signature is verified against installed `strands-agents`.
- `concierge/service.py` is an optional plus (FR-4.5) and may be omitted; nothing in the eval depends on it.
