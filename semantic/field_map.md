# Field / Domain-Name Mapping
# version: 0.2

Attendee vocabulary -> physical columns, so the agent can turn a natural-language
question ("what AI talks are on Tuesday?") into the right lookups. Synonyms live
here as governed content, not in the prompt.

| attendee term         | source   | column       | notes                               |
|-----------------------|----------|--------------|-------------------------------------|
| talk / session / topic| sessions | title        |                                     |
| track / theme         | tracks   | track_name   | join via track_id                   |
| room / where          | rooms    | room_name    | join via room_id                    |
| speaker / who         | speakers | speaker_name | join via session_id                 |
| when / time           | sessions | start, end   |                                     |
| day                   | sessions | day          | Mon / Tue                           |

## Track vocabulary (canonical)
infra, community, ai, career, devtools
