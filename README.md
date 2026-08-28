# Brawl Stars Stats API

A REST API that tracks Brawl Stars players over time.

Supercell's API only returns a snapshot: current trophies, and roughly the last 25 battles before the log rolls over. This service polls on a schedule and stores what it sees, so it can answer questions the official API can't — win rates over longer windows, per-brawler performance filtered by map and mode, and trophy progression over time.

Built to be used by a [Telegram bot](https://github.com/Youssef080808/Telegram-py-bot), but usable on its own.

**Status:** in development. Database, API client and battle parser done; storage and endpoints not yet built.

## Planned endpoints

```
POST   /players              Register a player for tracking
DELETE /players/{tag}        Stop tracking
GET    /players/{tag}        Current snapshot
GET    /players/{tag}/trophies   Trophy and ranked elo history
GET    /players/{tag}/battles    Stored battles, paginated
GET    /players/{tag}/winrate    Win/draw/loss counts
GET    /players/{tag}/brawlers   Per-brawler breakdown
```

The last two take filters as query parameters — `last`, `mode`, `map`, `type`, `brawler`, `top`, `min_matches` — which combine, so one endpoint covers every question rather than needing one per combination:

```
GET /players/{tag}/brawlers?map=Hard Rock Mine&type=soloRanked&top=5
```

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
```

`BRAWL_API_KEY` is a Supercell developer key. Requests are routed through [RoyaleAPI's proxy](https://docs.royaleapi.com/proxy), since Supercell locks keys to whitelisted IPs and this runs on infrastructure whose IP can change.

## Project structure

- `config.py` — settings and secrets, read from the environment
- `db.py` — schema and connection helper; run directly to create the tables
- `poller.py` — fetches player profiles and battle logs from the upstream API
- `parser.py` — turns raw battle JSON into rows

## Known limitations

- History only accumulates from when a player is registered; earlier matches are already gone upstream.
- A player who plays more than ~25 matches between polls will have gaps.
- Narrow filters can produce win rates over very few matches, so match counts are always returned alongside.