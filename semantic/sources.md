# Source Catalog
# version: 0.2  (add a source by adding a row here — no agent code changes)

The agent discovers sources from this catalog at runtime. It does NOT hardcode them.

| source_id | file               | grain       | description                                  |
|-----------|--------------------|-------------|----------------------------------------------|
| sessions  | data/sessions.csv  | session_id  | Talks: title, track, room, day, start/end    |
| tracks    | data/tracks.csv    | track_id    | Track name + theme for each track            |
| speakers  | data/speakers.csv  | session_id  | Who is speaking in each session              |
| rooms     | data/rooms.csv     | room_id     | Room name, capacity, floor                   |
