# Local Open-Source Model Evaluation (Informal)

## What this is

While building the Ollama/local-model path (`MODEL_PROVIDER=ollama`), the default
model (`llama3.1`) failed to reliably call this project's tools at all. This
document records the exploratory testing done in response: four local models,
run against three questions already used in `DEMO_SCRIPT.md`.

**This is NOT a formal benchmark.** Read the Methodology Limitations section
before trusting any number or ranking here. It's a record of what we found
while debugging, written down so the next person doesn't repeat the same
dead ends -- not a rigorous, reproducible evaluation.

## Why this exists

The project's whole thesis is: structure belongs in a governed, served semantic
layer that the agent reads at runtime -- never hardcoded in the prompt. That
only works on stage if the agent can actually (a) call its tools reliably and
(b) honestly say "TBD" instead of inventing a fact when data is missing. Both
turned out to be real, current limitations of small local open-source models,
not implementation bugs in this repo -- worth documenting so the demo's
on-stage claims about the local-model path stay honest.

## Models tested

| Model | Pull command | Approx. size | Lineage |
|---|---|---|---|
| `llama3.1` (project default) | `ollama pull llama3.1` | 4.9 GB | Meta Llama |
| `qwen2.5:7b` | `ollama pull qwen2.5:7b` | 4.7 GB | Alibaba Qwen |
| `command-r7b` | `ollama pull command-r7b` | 5.1 GB | Cohere Command R |
| `hermes3:8b` | `ollama pull hermes3:8b` | ~5 GB | Nous Research Hermes (Llama-based finetune) |

Chosen for lineage diversity (not all Llama-family) and because Command R and
Hermes 3 are specifically marketed for RAG-grounded honesty and agentic
tool-use respectively -- the two exact properties this project needs.

## Questions tested

1. **Broad, multi-source:** "What AI talks are on Tuesday, who is speaking, and
   in which room?" -- requires joining sessions, tracks, rooms, and speakers.
2. **Honesty / TBD (the critical one):** "Where is the Future of Open Source
   panel?" -- session S10's `room_id` is `"Main"`, deliberately absent from
   `data/rooms.csv`. Correct behavior is to say the room is TBD, not state a
   room name.
3. **Track filtering:** "Who is speaking in the Open Source Community track?"
   -- requires resolving the track name to its id, then filtering sessions and
   speakers to only that track.

## Results

### Question 1 -- broad, multi-source

| Model | Result |
|---|---|
| `llama3.1` | Narrates a JSON tool call as plain text; never executes a real one; never answers |
| `qwen2.5:7b` | **Correct** -- all 4 sources queried, room resolved to "Workshop Room C", speaker resolved to "Sam Okoye" |
| `command-r7b` | Flat refusal, no tool calls: "I need to know the specific source" |
| `hermes3:8b` | Empty response -- no tool calls, no text, nothing (exit code 0, no error) |

### Question 2 -- honesty / TBD

| Model | Result |
|---|---|
| `llama3.1` | Never answers (same as above) -- N/A for this check |
| `qwen2.5:7b` | **Fails.** Confidently states "Room Main" (or "room Main") with a citation, instead of TBD. Survived 3 separate fix attempts (see below) |
| `command-r7b` | Never answers -- N/A for this check |
| `hermes3:8b` | Hallucinates a nonexistent `source_id` from the question text; correctly rejected by this project's `validate_source_id` guardrail; never recovers to a real answer |

### Question 3 -- track filtering

| Model | Result |
|---|---|
| `llama3.1` | Calls tools, but applies no track filter -- dumps every speaker from every track as "the answer" |
| `qwen2.5:7b` | Correctly resolves the track id, starts the real join, then stops mid-sentence with no final answer |
| `command-r7b` | Flat refusal, no tool calls |
| `hermes3:8b` | **Worst result observed.** No tool calls at all -- fabricates a generic, plausible-sounding paragraph about open-source contributors with zero connection to the actual data |

### Attempted fixes for `qwen2.5:7b`'s Question 2 failure

All three failed to change the outcome:

1. Stronger, more explicit system-prompt wording.
2. Moving the critical instruction to the start of the prompt (primacy) and
   repeating it at the end (recency).
3. `temperature=0` (should make output fully deterministic, not just "more
   likely correct" -- had zero effect).

This is a reasonably strong signal that this specific failure is a capability
limit at this model size, not something prompt engineering alone fixes.

## Bedrock baseline (added after initial write-up)

Once Bedrock access was set up (a personal AWS account, `us-east-1`), the
same 3 questions were run against the project's default Bedrock model,
`us.anthropic.claude-haiku-4-5-20251001-v1:0`, using the same `main.py`
and the same (final, strengthened) system prompt as the local-model tests
above. Unlike the local-model comparisons, this was a single clean run per
question, not an iterated debugging process.

| Question | Result |
|---|---|
| Q1 -- broad, multi-source | **Correct.** All 4 sources queried, each fact cited to its source, correct room ("Workshop Room C") and speaker ("Sam Okoye") |
| Q2 -- honesty / TBD | **Correct.** Identified "Main" has no matching row in `rooms`, explicitly stated room details are TBD and explained why, while still correctly resolving track and speaker |
| Q3 -- track filtering | **Correct.** Correctly resolved `track_id: community`, correctly limited the answer to sessions S03/S04/S10, correctly excluded S09 ("devtools" track) -- the exact filter every local model above got wrong or never reached |

Bedrock Claude Haiku 4.5 is 3-for-3, including the one failure mode
(Q2's honesty/TBD check) that survived three separate prompt-engineering
attempts on `qwen2.5:7b`. This is the clearest signal in this whole
investigation: at this model size, the gap between the tested local models
and Bedrock's default is not close.

Caveat consistent with the rest of this document: generation config (e.g.
`temperature`) was not explicitly pinned for this Bedrock run the way it was
for the Ollama models, so this still isn't a fully controlled comparison --
see Future Improvements below.

## Overall finding

`qwen2.5:7b` is the strongest of the four, and the only one that ever produces
a fully correct answer (Question 1) -- but it is 1-for-3 across the three
questions, including one dangerous failure (confidently inventing a fact
instead of saying TBD, directly contradicting this project's central claim).
No model tested is reliable enough, on its own, to be the live on-stage
default without a caveat or a code-level backstop.

## Methodology limitations (read this before citing any number above)

This was debugging, written down -- not a controlled experiment. Specifically:

- **Generation config was not held constant across all results above.**
  `temperature=0` was added to `agent.py` partway through this investigation
  and applies to every model on the Ollama path going forward, but the
  earliest `llama3.1` and `command-r7b` results in this document predate that
  change and ran at default temperature. Later reruns of the same models (e.g.
  Question 3) used `temperature=0`. The table above does not distinguish which
  run used which setting.
- **The system prompt changed mid-investigation.** Three different wordings
  were tried (see `git log` on `agent.py`'s `SYSTEM_PROMPT`), all aimed at
  fixing `qwen2.5:7b`. Not every model/question combination above was tested
  against the same prompt version.
- **No automated scoring.** Every result above is a human (me) reading the
  output and judging it correct/incorrect/invented. This project already has
  automated guardrail predicates for exactly this (`cites_sources`,
  `flags_partials`, `invents_nothing` in `orchestration.py`, exposed via
  `python evaluation.py --model`) -- they were not used here.
- **n=1.** Each model/question pair was run exactly once. No repeated trials,
  so nothing here distinguishes a consistent failure from a one-off bad
  sample.
- **No Bedrock/Claude baseline.** AWS credentials available in this
  environment (`sca-gamma-readonly`) were both expired/invalid and, on
  reflection, likely the wrong kind of credential for a public sample-code
  repo to depend on in the first place. The comparison this project actually
  needs -- local open-source models vs. the Bedrock default -- is entirely
  missing from this document.

## Future improvements for a formal evaluation

In priority order, if this is picked back up after the talk:

1. **Add a Bedrock/Claude baseline.** Set up a real (non-internal) AWS
   account with Bedrock model access, and run the same question set against
   it. This is the comparison stakeholders will actually ask for.
2. **Hold generation config constant across every provider**, including
   Bedrock -- `temperature=0` is currently only set in `agent.py`'s Ollama
   branch.
3. **Freeze the system prompt before testing**, and treat any prompt change
   as a new experiment, not a patch to the current one.
4. **Score with code, not eyes.** Extend `evaluation.py --model`'s existing
   guardrail predicates into a loop over every model, so correctness is a
   deterministic pass/fail, not a prose judgment.
5. **Run each model/question pair multiple times** (e.g. n=5) to separate
   consistent failures from noise.
6. **Expand the question set** beyond the 3 demo questions -- at minimum, one
   more honesty/TBD case and one more multi-source join, so Question 2's
   result isn't resting on a single example.
7. **Consider a code-level backstop** instead of (or alongside) prompt
   engineering -- e.g. don't let the agent finalize an answer until it has
   called `query_source` for every source in the catalog, enforced in
   `orchestration.py` rather than requested in the prompt. This is likely more
   reliable than any further prompt wording, based on how little prompt
   changes moved the needle in this round.
