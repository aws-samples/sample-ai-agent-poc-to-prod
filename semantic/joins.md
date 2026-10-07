# Join Semantics
# version: 0.2

How sources relate. This is the single place correlation logic lives. Add a
source to sources.md + a row here and the agent can immediately use it ---
"build once, use everywhere."

## Keys and joins
- sessions.track_id  -> tracks.track_id     (enrich a talk with its track name/theme)
- sessions.room_id   -> rooms.room_id        (enrich a talk with room name/floor)
- sessions.session_id -> speakers.session_id (attach the speaker(s) to a talk)

## Correctness rules (the agent MUST honor these)
1. Join only on the keys above.
2. Always state which source each fact came from (e.g. room name from `rooms`).
3. If a talk references a room/track/speaker that is MISSING from its source,
   report it as PARTIAL ("room TBD") -- never drop the talk, never invent a value,
   never present an incomplete answer as complete.
