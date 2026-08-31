# Brawl Stars Stats API

A REST API that tracks Brawl Stars players over time.

Supercell's API only returns a snapshot: current trophies, and roughly the last 25 battles before the log rolls over. This service polls on a schedule and stores what it sees, so it can answer questions the official API can't — win rates over longer windows, per-brawler performance filtered by map and mode, and trophy progression over time.

Built to be used by a [Telegram bot](https://github.com/Youssef080808/Telegram-py-bot), but usable on its own.

**Status:** in development. Collection works end to end, and all read endpoints are built. Registering a player still has to be done directly against the database.

## Endpoints

```
GET    /health                   Liveness check
GET    /players/{tag}            Tracking info and latest snapshot
GET    /players/{tag}/record     Win/draw/loss counts, filtered
GET    /players/{tag}/brawlers   Per-brawler breakdown, ranked
GET    /players/{tag}/trophies   Trophy and ranked elo history
GET    /players/{tag}/battles    Stored battles, paginated
DELETE /players/{tag}            Stop tracking
```

Still to build: `POST /players`, to register a player for tracking.

Interactive documentation is generated automatically at `/docs`.

`record` and `brawlers` take filters as query parameters — `last`, `mode`, `map`, `type`, `brawler`, `top`, `min_matches` — which combine, so one endpoint covers every question rather than needing one per combination:

```
GET /players/{tag}/record?mode=soloShowdown&brawler=WENDY&last=50
```

`last` means the player's last N battles overall, then filtered — not the last N matching the filter. So narrow filters return small samples, which is why counts are returned rather than a percentage. The caller decides whether draws belong in the denominator.

`brawlers` sorts by win rate with match count as a tiebreak, and `min_matches` drops brawlers with too few games so a single lucky win doesn't top the list.

Tags are accepted with or without `#` and in any case, since `#` starts a URL fragment and never reaches the server.

## Data model

Three tables, defined in `db.py`: `players`, `battles`, and `snapshots`.

`battles` is keyed on `(player_tag, battle_time)` — a player can only be in one battle at a given second. Since each poll returns an overlapping window of the same battles, this plus `INSERT OR IGNORE` makes re-polling safe.

## Parsing

Battles come back in three shapes, and the parser normalises all of them into one row format:

| Variant | Players | Outcome field | `trophyChange` | `starPlayer` |
|---|---|---|---|---|
| Showdown | flat list | `rank` | present | absent |
| 3v3 trophy | nested by team | `result` | present | present |
| 3v3 competitive | nested by team | `result` | absent | present |

Win, draw and loss mean different things per mode — top 4 wins a solo Showdown, top 2 wins a duo — so a normalised `outcome` is derived on insert. The raw `rank` and `result` are stored alongside it, so the rules can change without the underlying data being lost.

Fields that are legitimately absent stay null rather than being defaulted, since the distinction matters: `star_player` is null in Showdown because the mode has no star player, which is not the same as the player not being it.

## Setup

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt

export BRAWL_API_KEY="your_key_here"
python3 db.py          # creates the tables
python3 poller.py      # polls every tracked player once
uvicorn api:app --reload
```

`BRAWL_API_KEY` is a Supercell developer key. Requests are routed through [RoyaleAPI's proxy](https://docs.royaleapi.com/proxy), since Supercell locks keys to whitelisted IPs and this runs on infrastructure whose IP can change.

The poller runs once and exits rather than looping, so scheduling stays outside the program — cron or a container schedule, rather than a sleep in the code.

## Project structure

- `config.py` — settings and secrets, read from the environment
- `db.py` — schema, connection helper, and storage functions
- `poller.py` — fetches from the upstream API and stores results
- `parser.py` — turns raw battle JSON into rows
- `api.py` — HTTP endpoints

## Known limitations

- History only accumulates from when a player is registered; earlier matches are already gone upstream.
- A player who plays more than ~25 matches between polls will have gaps.
- A poll that fails partway leaves a snapshot written but no battles, since the two are stored separately.
- Narrow filters can produce records over very few matches, so counts are always returned alongside.