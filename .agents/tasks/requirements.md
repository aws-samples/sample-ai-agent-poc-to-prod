# Requirements — Conference Schedule Concierge (poc-to-prod-demo)

## Summary

Build a production-grade, clearly **layered** example application for the All Things Open 2026 talk *"Designing Production-Grade Agentic Systems: From Prototype to Scalable Infrastructure."* The application is a **Conference Schedule Concierge** that helps an attendee choose which sessions to attend at a fictional **DevConf 2026**, over synthetic data.

The central thesis the code must demonstrate: agents don't fail in production because of the model — they fail because the data underneath isn't reusable or AI-ready. The fix is a **governed, versioned semantic layer** (source catalog + term/field mapping + join rules + guardrail rules) that the agent reads **at runtime**, instead of hardcoding data structure in the LLM system prompt. Tagline: *"Build once, use everywhere."* Talk arc: prototype → AI-ready data foundation → scale.

This project extends the reference implementation at `ATO2026_Working_Materials/semantic-layer-agent`. The reference's demo script beats, data invariants, and the deterministic-eval property must be preserved. The build must favor open source, keep dependencies light, and use Amazon Bedrock via the open-source Strands Agents SDK while keeping the model/provider swappable in design.

### Assumptions
- A1. Target implementation language is **Python 3.10+** (reference uses 3.10+ syntax such as `list[dict]`).
- A2. The project is new (target dir empty apart from `.agents/`); nothing from the reference is in-place and all carried-over artifacts are copied/adapted into the new layered layout.
- A3. The dataset may be enriched (more sessions/tracks/rooms/speakers) but stays fictional, and the specific S10 "Main" room gap and documented join keys are preserved exactly.
- A4. "No network/model" means the core contract eval imports only the standard library plus the project's own modules and never calls Bedrock or any network service.
- A5. Observability/eval dependencies stay light; OpenTelemetry-style spans are implemented with minimal/no heavy deps (structured logging is acceptable if a span library would be heavyweight).

---

## Layer architecture (requirement framing)

The deliverable must expose four layers with clean, visible module boundaries, each its own package/module with a docstring stating its responsibility and boundary. These boundaries are the architecture-diagram slide, so they must be legible in the source tree.

| # | Layer | Responsibility |
|---|-------|----------------|
| 1 | Data Platform | Reusable, domain-agnostic foundation: source connectors, loader/registry/catalog driven by the semantic layer's source list, typed interface. |
| 2 | Semantic | Governed, versioned artifacts (markdown catalog/field_map/joins + optional machine-readable schema), served at runtime via a tool. |
| 3 | Orchestration | Modular Strands tools (`get_semantic_layer`, `query_source`, join/enrichment engine) composed into a multi-step workflow. |
| 4 | Agent / Application | The concierge: required CLI entry; optional thin API entry. LLM system prompt carries no schedule structure. |

---

## Functional Requirements

### FR-1 — Data Platform layer (reusable foundation)
- FR-1.1 Provide source connectors that read tabular rows from the backing files (CSV at minimum, matching the reference sources).
- FR-1.2 Provide a loader/registry/catalog that is **driven by the semantic layer's source list** (sources.md), not by a hardcoded dictionary in agent code. Adding a source to the catalog must make it loadable without editing data-platform or agent code.
- FR-1.3 Expose a clean, typed, **domain-agnostic** interface, at minimum: `list_sources()`, `get_source(id)`, and a way to read rows for a source. Nothing in this interface may reference conference-specific concepts (sessions, tracks, rooms, speakers).
- FR-1.4 Reusability must be explicit in both code (docstrings/types stating the layer is domain-agnostic and reusable) and docs (README reusable-data-platform story describing how a different, non-conference app could reuse it).
- FR-1.5 Reading an unknown/invalid source id must return a structured error (not raise an unhandled exception, not invent data), consistent with the reference `query_source` behavior.

### FR-2 — Semantic layer (governed, versioned)
- FR-2.1 Carry over and adapt the three governed markdown artifacts: a **source catalog** (`sources.md`), a **field/term mapping** (`field_map.md`), and **join semantics** (`joins.md`). Each must carry a version marker.
- FR-2.2 The join semantics must document exactly these keys and must remain the single place correlation logic lives:
  - `sessions.track_id → tracks.track_id`
  - `sessions.room_id → rooms.room_id`
  - `sessions.session_id → speakers.session_id`
- FR-2.3 The semantic layer must state the guardrail/correctness contract: join only on documented keys; cite the source of every fact; if a room/track/speaker is missing, report it TBD/partial — never drop the item, never invent a value, never present an incomplete answer as complete.
- FR-2.4 Provide an **optional machine-readable schema** alongside the markdown (e.g., JSON/YAML describing sources + keys) so the data platform and eval can consume it programmatically; the markdown remains the governed, human-reviewable source of truth.
- FR-2.5 Adding a source/track/room must be an edit to semantic-layer content and data only — no change to orchestration or agent code.
- FR-2.6 The layer must be served to the agent at runtime via a tool (see FR-3.1); the layer must be versioned so quality-vs-layer-version drift can be shown later.

### FR-3 — Orchestration layer (modular Strands tools)
- FR-3.1 Provide a `get_semantic_layer` Strands tool that returns the governed layer (catalog + field map + join semantics) as served content.
- FR-3.2 Provide a `query_source(source_id)` Strands tool that returns rows for one catalogued source, delegating to the data-platform interface, and returns a structured error for unknown ids.
- FR-3.3 Provide a deterministic **join/enrichment engine** (equivalent to the reference `enrich_sessions()`) that enriches each session with track name, room name, and speaker(s) following the documented join keys, and sets a `partial` flag plus TBD markers when a referenced track/room/speaker is missing. This engine must be importable and callable with no model/network.
- FR-3.4 Tools must be small and composable; the enrichment engine must be reused by the eval as the deterministic reference.
- FR-3.5 Tools must remain importable and testable even when the Strands SDK is not installed (reference degrades gracefully via a fallback `tool` decorator).

### FR-4 — Agent / Application layer (the concierge)
- FR-4.1 Provide a CLI entry invoked as `python main.py "question"` that matches the DEMO_SCRIPT usage and default question behavior.
- FR-4.2 The LLM **system prompt must carry no schedule structure** — no sources, keys, room/track mappings, or join rules. It must instruct the agent to call `get_semantic_layer` first, then `query_source` per needed source, join only on documented keys, cite each fact's source, and flag missing data as TBD.
- FR-4.3 The agent must be a Strands agent using Amazon Bedrock as the default model provider, with the **model/provider swappable by configuration** (model id/provider as a setting, not hardcoded in logic). Design must be provider-agnostic.
- FR-4.4 If the SDK is not installed or the model is not configured, the CLI must fail gracefully with an actionable message (reference prints install guidance and the error) rather than crashing.
- FR-4.5 Optional (plus, not required): a thin API/service entry for the scale story. If included, it must not change CLI behavior and must reuse the same orchestration/semantic/data layers.

### FR-5 — Theme A: Evaluation & Scoring
- FR-5.1 Carry over and extend the reference's deterministic **contract checks**: (1) layer served (catalog + join semantics present), (2) all sources load from the catalog, (3) a session enriches correctly across sources on the documented keys, (4) a session with a missing room is flagged TBD/partial — not dropped or invented.
- FR-5.2 Add a **quality/scoring layer** that quantifies output quality and catches hallucinations early: scored checks that a response cites sources, flags partials, and invents no room/track/speaker absent from the data.
- FR-5.3 Core contract tests (FR-5.1) and the deterministic scoring checks that operate on the enrichment engine's output must run with **no model and no network**, suitable for CI.
- FR-5.4 Provide an **optional model-in-the-loop scoring mode**, clearly separated from the deterministic path (separate command/flag/module), that may call the model to score real agent responses. It must never be required for the core eval to pass.
- FR-5.5 The full eval must be runnable with a **single command**.

### FR-6 — Theme B: Observability
- FR-6.1 Emit **structured** tracing/logging capturing, per step: latency, which tools were called, and token/step counts.
- FR-6.2 Represent **model drift as quality vs. semantic-layer version** — observability output must associate a quality signal with the layer version so drift across versions can be shown.
- FR-6.3 Prefer open-source/standard approaches: structured logging, and OpenTelemetry-style spans if feasible without heavy dependencies. Keep deps light.
- FR-6.4 Observability must be usable from the orchestration/agent path and must not break the no-network eval property.

### FR-7 — Theme C: Cost-Performance
- FR-7.1 Make the model id/config a **setting** (ties to FR-4.3) to allow right-sizing the model.
- FR-7.2 **Cache the served semantic layer** so repeated agent steps don't re-read/re-assemble it each call.
- FR-7.3 Keep agent context small (don't inline full data into the prompt; rely on runtime tool reads).
- FR-7.4 Include **token/cost accounting** in the observability output.

### FR-8 — Theme D: Security guardrails
- FR-8.1 Treat tool output as **untrusted DATA, not instructions** — the agent/orchestration must not execute or follow directives embedded in source rows or layer content beyond their data role.
- FR-8.2 Enforce **least-privilege tool access**: tools expose only reads over catalogued sources; no write/delete/arbitrary-file access.
- FR-8.3 Enforce **authorization/validation at the source boundary** and **input validation on source ids** (only catalogued ids are honored; unknown ids return a structured error, never a file read outside the catalog).
- FR-8.4 Enforce the **never-invent / cite-sources / flag-TBD** contract in code paths (the enrichment engine and guardrail checks), not only in prose.
- FR-8.5 Include a **brief threat model** in docs covering prompt injection and data leakage and how each is mitigated.

### FR-9 — Theme E: Modularity & Extensibility
- FR-9.1 Adding a track/room/source must be an edit to the **semantic layer + data**, not agent code (ties to FR-1.2, FR-2.5).
- FR-9.2 Preserve **DEMO_SCRIPT Beat 4** working end to end: add a track row + a session (or a new source) by editing the layer/data, re-run a matching question, and the new content appears with no code change.

### FR-10 — Data & synthetic content
- FR-10.1 Carry over the four synthetic sources (sessions, tracks, speakers, rooms) with the documented grain and columns. The dataset **may** be enriched with more sessions/tracks/rooms/speakers, but must stay fictional (DevConf 2026, no real schedules, no internal/company/project names).
- FR-10.2 **Preserve the S10 gap exactly**: session S10 ("Panel: The Future of Open Source") references `room_id = "Main"`, which must remain **absent** from rooms.csv, to drive the on-stage "room TBD" partial-result moment.
- FR-10.3 Preserve the fact anchors the eval and demo narration depend on (e.g., an AI/Agents session that joins to "Workshop Room C" with a known speaker, so Beat 3's spoken claims and the enrichment test remain valid). If the dataset is enriched, these anchors must still hold or the eval/demo narration must be updated in lockstep.

### FR-11 — Documentation & deliverables
- FR-11.1 Top-level **README.md** must describe the layered architecture with an ASCII or mermaid diagram, state how each of the five themes is addressed and **where in code**, tell the reusable-data-platform story, and give setup/usage and how to run the eval.
- FR-11.2 README doc style must **state what IS needed directly** — no "X not required, but…" framing.
- FR-11.3 Carry over and adapt **DEMO_SCRIPT.md**: update paths/commands to the new layout, preserve the beats (0–4) and the TBD moment, and keep the fallback "run the eval" option.
- FR-11.4 Provide **requirements.txt** pinned to reasonable versions: `strands-agents`, `strands-agents-tools`, plus minimal, justified light open-source deps only.
- FR-11.5 Provide **.env.example** (Bedrock/provider config, e.g., region + model id) and **.gitignore**.
- FR-11.6 Keep docs framework-neutral in tone: Strands is the concrete SDK on screen; the pattern is model/framework-agnostic.
- FR-11.7 Include the educational/demo/synthetic/fictional **disclaimer** matching the reference README.
- FR-11.8 Each layer module/package must carry a docstring stating its responsibility and boundary.

---

## Non-Functional Requirements

- NFR-1 **Dependency minimalism**: only the SDK plus light, justified open-source deps; each added dependency justified in the README/requirements. Open source preferred throughout.
- NFR-2 **Determinism for CI**: core contract eval and deterministic scoring must produce identical results across runs with no network/model.
- NFR-3 **Provider-agnostic design**: swapping the model provider/model id must be a configuration change, not a code refactor.
- NFR-4 **Portability**: must run on a presenter's laptop (Windows/macOS/Linux) with Python 3.10+; the no-model eval must run with just a `pip install` of light deps (or stdlib only).
- NFR-5 **Legible layering**: the four layers must be separable packages/modules such that the source tree reads as the architecture diagram.
- NFR-6 **Demo faithfulness**: on-stage commands, timing beats, and spoken claims from DEMO_SCRIPT must remain accurate against the shipped code and data.
- NFR-7 **Light observability**: tracing/spans must not materially slow the demo or pull in heavy dependencies.

---

## Invariants that MUST be preserved (checklist)

- INV-1 **S10 "Main" room gap**: S10 references room_id "Main"; "Main" is absent from rooms.csv. Keep it.
- INV-2 **Join keys**: `sessions.track_id→tracks.track_id`, `sessions.room_id→rooms.room_id`, `sessions.session_id→speakers.session_id`. Unchanged.
- INV-3 **No schedule structure in the LLM system prompt**: sources/keys/joins live only in the served semantic layer.
- INV-4 **Deterministic eval with no network/model** for the core contract tests (and the deterministic scoring checks).
- INV-5 **Guardrail contract**: cite the source of every fact; missing data → TBD/partial; never invent; never present incomplete as complete.
- INV-6 **Demo beats 0–4** preserved, including the TBD moment (Beat 3) and the add-a-track-by-editing-the-layer payoff (Beat 4), plus the "run the eval" fallback.
- INV-7 **Add-a-source = edit content, not code**: the catalog/registry is driven by the semantic layer's source list.
- INV-8 **Everything fictional/synthetic**: DevConf 2026, no real schedules, no internal/company/project names.
- INV-9 **Tools importable/testable without the SDK installed** (graceful degradation).

---

## Acceptance Criteria

1. The source tree exposes four distinct packages/modules — data platform, semantic, orchestration, agent/application — each with a docstring stating responsibility and boundary. (FR-layers, NFR-5)
2. `python main.py "What AI talks are on Tuesday, who is speaking, and in which room?"` runs the Strands agent against Bedrock (when configured) and produces an answer that cites the source of each fact. (FR-4.1, FR-4.2)
3. Grepping the agent's system prompt reveals **no** source names, column names, join keys, or room/track mappings. (INV-3, FR-4.2)
4. The data-platform public interface (`list_sources()`, `get_source(id)`, read rows) contains no conference-specific vocabulary and is documented as reusable/domain-agnostic. (FR-1.3, FR-1.4)
5. The source catalog/registry is populated from the semantic layer's source list; adding a source row (plus its data) makes `query_source` return its rows with no code change. (FR-1.2, FR-2.5, INV-7)
6. A single command runs the eval; with no network and no model configured, all core contract checks and deterministic scoring checks pass. (FR-5.1, FR-5.3, FR-5.5, NFR-2, INV-4)
7. The eval asserts: layer served; all sources load; a known AI/Agents session enriches to its track name, "Workshop Room C", and its speaker on the documented keys with `partial=False`; and S10 has `partial=True` with a TBD room. (FR-5.1, FR-10.2, FR-10.3, INV-1, INV-2)
8. A scored quality check fails a response that omits source citations, hides a partial, or names a room/track/speaker absent from the data. (FR-5.2)
9. An optional model-in-the-loop scoring mode exists behind a separate command/flag and is never required for the core eval to pass. (FR-5.4)
10. Running the agent emits structured per-step traces including latency, tools called, and token/step counts, and associates a quality signal with the semantic-layer version. (FR-6.1, FR-6.2, FR-7.4)
11. Observability uses structured logging and (if present) lightweight OpenTelemetry-style spans with no heavy deps. (FR-6.3, NFR-7)
12. The served semantic layer is cached so repeated steps within a run do not re-assemble it; the model id/provider is read from configuration/.env. (FR-7.1, FR-7.2, FR-4.3, NFR-3)
13. `query_source` with an unknown/invalid id returns a structured error and does not read any file outside the catalog. (FR-1.5, FR-8.3)
14. The README includes a threat model covering prompt injection (tool output treated as data) and data leakage (least-privilege, read-only tools, source-boundary authorization). (FR-8.1, FR-8.2, FR-8.5)
15. Performing DEMO_SCRIPT Beat 4 — adding a track row + a session (or a new source) by editing the semantic layer/data — and re-running a matching question surfaces the new content with no code change; the eval still passes. (FR-9.1, FR-9.2, INV-6)
16. README documents the layered architecture with an ASCII/mermaid diagram, maps each of the five themes to where it lives in code, tells the reusable-data-platform story, and uses no "X not required, but…" framing. (FR-11.1, FR-11.2)
17. DEMO_SCRIPT.md is present with updated paths/commands, preserved beats 0–4, the TBD moment, and the "run the eval" fallback. (FR-11.3, INV-6)
18. requirements.txt pins `strands-agents` and `strands-agents-tools` plus only minimal justified light deps; `.env.example` and `.gitignore` are present; the README carries the educational/demo/synthetic/fictional disclaimer. (FR-11.4, FR-11.5, FR-11.7)
19. All data is fictional (DevConf 2026); no real schedules or internal/company/project names appear anywhere. (FR-10.1, INV-8)
20. Tools import and the enrichment engine runs with the Strands SDK uninstalled (graceful degradation), proving the no-network eval path. (FR-3.5, INV-9)

---

## Out of Scope

- Real conference data, live schedule feeds, or any non-synthetic/internal data.
- Persistent databases, auth servers, or production infrastructure provisioning (the "scale" story is narrative + optional thin API, not a deployed system).
- A web/GUI front end. CLI is required; a thin API is an optional plus only.
- Multi-agent orchestration (the reference and this build are single-agent).
- Fine-tuning, training, or model hosting; the model is consumed via Bedrock/Strands.
- Non-CSV source connectors beyond what's needed to demonstrate reusability (the typed interface should allow them, but implementing additional backends is not required).
