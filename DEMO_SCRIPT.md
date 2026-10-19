# On-Stage Demo Script — Conference Schedule Concierge

- **Talk:** Designing Production-Grade Agentic Systems: From Prototype to Scalable Infrastructure
- **Session:** Tue Oct 20, 2026 · 12:00–12:30 PM ET · All Things Open (Raleigh)
- **Demo length:** ~5 min (target), 6 min hard cap
- **Tooling:** Strands Agents SDK (open-source), Python, synthetic data — fictional "DevConf 2026", no project names, no internal infra
- **One idea to land:** a reusable, AI-ready data foundation. How data relates belongs in a *governed, served semantic layer*, not in the prompt. Build once, use everywhere.
- **Code:** published to AWS Samples.

> **OS-command note.** The demo laptop may be Windows (PowerShell) or Unix. The
> Beat-1 structure scan below ships in both forms — `Select-String` (PowerShell)
> and `grep -iE` (macOS/Linux). The eval is invoked the same shell-agnostic way
> on every OS: `cd` into the project, then `python evaluation.py`.

> **Provider note.** The demo can run entirely against a local open-source model
> with no AWS: set `MODEL_PROVIDER=ollama` in `.env` (the default), `ollama pull
> llama3.1`, `ollama serve`, and run the same `python main.py "..."`. The
> pre-flight model-id / credentials / region checks below apply only to the
> Bedrock path (`MODEL_PROVIDER=bedrock`). For the live/recorded run of this
> script, Bedrock (Claude Haiku 4.5) is the model actually used — local models
> tested were inconsistent at this script's exact questions (see
> `MODEL_EVALUATION.md`), so don't swap to Ollama for the live take without
> re-verifying each beat first.

---

## Why this example works for *this* room
It's a conference assistant, demoed at a conference, for people who've spent two days reading schedules. Everyone instantly gets talks → tracks → rooms → speakers — no data background needed — so the audience watches the *pattern*, not the domain.

---

## Pre-flight checklist (before you go on)
- [ ] Terminal font ↑ (18pt+), high contrast, window ~110 cols so tables don't wrap
- [ ] `pip install -r requirements.txt` already done in the venv
- [ ] `.env` configured (Bedrock creds) — OR plan to run the eval (no model needed) as the live portion
- [ ] **Verify the model id is current and enabled** — ids get retired (a dead one
      returns `ResourceNotFoundException`). Confirm `BEDROCK_MODEL_ID` in `.env` is in
      `aws bedrock list-inference-profiles --region $env:AWS_REGION`, then do ONE live
      run of `python main.py "..."` to confirm it answers. Do this the morning of.
- [ ] **Fresh AWS credentials** — `aws sts get-caller-identity` succeeds (expired tokens
      give `ExpiredTokenException`). Re-auth right before you go on.
- [ ] **Shell environment is clean** — `AWS_REGION` matches the region where your model
      is enabled (a stale env var pointing at the wrong region fails even with good creds)
- [ ] **Fallback video recorded** (full run) and open in a browser tab
- [ ] Two terminal tabs: (1) project root, (2) `semantic/` open to show
- [ ] Pre-stage the Beat-4 edit (new track row + session) in a scratch file to paste
- [ ] `clear` the terminal; commands pre-seeded in history

---

## The arc (maps to prototype → production → scale)

| Beat | Time | On screen | What you SAY (gist) |
|------|------|-----------|---------------------|
| 0. Setup | 0:00–0:30 | Project tree (the ~6 flat files) | "One agent, a conference schedule across four sources. The tree **is** the architecture diagram. Watch *where* the logic that relates them lives." |
| 1. The prototype trap | 0:30–1:30 | `agent.py` prompt | "The naive build hardcodes 'this track is in that room' into the prompt. Works day one; drifts the moment the schedule changes." |
| 2. The turn — semantic layer | 1:30–3:00 | `semantic/*.md` | "Pull it out into a governed, versioned layer: catalog, term map, join rules. The agent reads it at runtime." |
| 3. Honesty under missing data | 3:00–4:00 | `python main.py "Where is the Future of Open Source panel?"` | "Same agent. Flags the room it can't find as TBD instead of inventing it." |
| 4. Build once, use everywhere | 4:00–5:00 | edit `data/`, re-run | "Add a track and a talk by editing the *data*, not the code. Re-run — it just appears." |

---

## Full narration + actions

### Beat 0 — Setup (0:00–0:30)
**Action:** show the project tree — point at the ~6 flat files `data_platform.py semantic.py orchestration.py agent.py evaluation.py main.py` and the `semantic/` folder of governed markdown.
**Say:**
> "This is a concierge for a conference — four data sources: the sessions, the tracks, the rooms, and the speakers. Six small files, one per layer — that's the architecture diagram, the tree *is* the diagram, each file reading only the one below it. I'll ask it the kind of thing you've all asked this week: what's on, who's speaking, which room. The whole demo is about one question — where does the agent's knowledge of how these connect actually live?"

### Beat 1 — The prototype trap (0:30–1:30)
**Action:** run the hardcoded-prompt agent live, change the data under it, rerun.
**Say:**
> "In most prototypes it lives in the prompt: 'the AI track is in Room C, speakers are in this file, join them like so.' Watch what that does."

```
python main.py --prototype "What AI talks are on Tuesday, who is speaking, and in which room?"
```
> "Workshop Room C — looks right, because it matches today's schedule."

**Action:** edit `data/sessions.csv`, move the two AI track sessions (`S05`,
`S06`) from room `C` to room `A`. Rerun the exact same command.
> "I just moved the AI track to a different room. Same prompt, same question, rerun —"

```
python main.py --prototype "What AI talks are on Tuesday, who is speaking, and in which room?"
```
> "— still says Room C. It's frozen on facts baked into the prompt. That's the prototype that doesn't survive contact with a real, changing schedule."
>
> *(Then, on the same changed data:)* "Here's the agent we actually built, same question:"

```
python main.py "What AI talks are on Tuesday, who is speaking, and in which room?"
```
> "Reads the data fresh, every time. No drift."

**(Revert the test edit before Beat 2 — `git checkout data/sessions.csv`, or
undo the room change — so the rest of the demo runs on the real schedule.)**

**Backup / cross-platform proof (if live editing feels risky on stage):**
`python evaluation.py` — check #5 (`prompt_no_structure`) proves in code that
the real agent's prompt carries no schedule structure at all, no live edit
needed. Keep this as your fallback, not your primary beat — it only proves
absence, not the actual drift the audience just watched above.

### Beat 2 — The turn: a served semantic layer (1:30–3:00)
**Action:** open the three files in `semantic/`, then point at the small source dict in `semantic.py` as the machine-readable mirror of `sources.md`.
**Say:**
> - `sources.md`: "A catalog — the four sources and their keys. Add a row to add a source."
> - `field_map.md`: "Attendee words → columns. 'Talk', 'who', 'where' map to real fields here, as governed content."
> - `joins.md`: "The important one: the keys — a talk joins to its track by `track_id`, its room by `room_id`, its speakers by `session_id` — plus the rules: cite the source of every fact, and if something's missing, say TBD. Never invent."
> - `semantic.py`'s `list_sources()` dict: "And here's the one small place code mirrors that catalog — four lines, with a comment saying 'add a row in sources.md and here.' Same content, in code."
>
> "This is versioned, reviewable, testable. Any agent — any host — that reads this layer gets the same correct behavior."

### Beat 3 — Honesty under missing data (3:00–4:00)
**Action:** `python main.py "Where is the Future of Open Source panel?"`
**Say:**
> "You already watched it join sources and answer correctly back in Beat 1. Here's the other half of production-grade: what happens when the data's incomplete."
>
> "Watch this — that panel's room isn't in the room source. A prototype would hallucinate a room. Ours says **room TBD** and tells you why. That honesty *is* the production-grade behavior."

**Fallback (no network):** run `python evaluation.py` — same join/TBD logic, deterministic, no network. Say: "Let me run our eval so you can see the contract hold without trusting the room's wifi." Nine checks print PASS and the suite ends with "All eval checks passed."

**Observability beat (optional, ~10s):** point at the `[timing]` line each tool
call prints — "that one timing line is the seam: in production this is exactly
where an OpenTelemetry span goes to watch latency and drift, without a heavyweight
tracing stack today."

### Beat 4 — Build once, use everywhere (4:00–5:00)
**Action:** paste a pre-staged new track row into `data/tracks.csv` + a session into `data/sessions.csv`, re-run a matching question. (Data-only edit — no code change, no reload.)
**Say:**
> "Here's the payoff. A new track just got added to the conference. I update the *data* — not the agent, not the prompt — and re-run. There it is. The agent was built once; the schedule grows by editing governed content and data. That's the extensibility that lets an agent graduate from prototype to something you'd actually run at scale — same pattern on your laptop or behind a gateway."

**Hand-off line (to the scale slide):**
> "The agent didn't change. The layer and the data did. Logic as served, versioned content — that's what carries you from prototype to scalable infrastructure."

---

## If the demo is cut for time (30-min reality)
Drop Beat 4's live edit; say it in one line over the slide. Keep Beats 2–3 (the layer + one run incl. the TBD moment) — that's the irreducible core.

## Framing notes
- Keep narration framework-neutral: Strands is the open-source SDK on screen; the *pattern* is model- and framework-agnostic. Say so.
- Don't claim the semantic layer is novel — it's a known data concept; the contribution is applying it to agent orchestration and making it runnable + open-source.
- Everything on screen is a fictional conference — not ATO's real schedule.
