# Brawl Stars Stats API

A REST API that tracks Brawl Stars players over time.

Supercell's API only returns a snapshot: current trophies, and roughly the last 25 battles before the log rolls over. This service polls on a schedule and stores what it sees, so it can answer questions the official API can't — win rates over longer windows, per-brawler performance filtered by map and mode, and trophy progression over time.

Built to be used by a [Telegram bot](https://github.com/Youssef080808/Telegram-py-bot), but usable on its own.

**Status:** in development. Database layer done; poller and endpoints not yet built.

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

## Setup

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt

export BRAWL_API_KEY="your_key_here"
python3 db.py          # creates the tables
```

`BRAWL_API_KEY` is a Supercell developer key. Requests are routed through [RoyaleAPI's proxy](https://docs.royaleapi.com/proxy), since Supercell locks keys to whitelisted IPs and this runs on infrastructure whose IP can change.

## Known limitations

- History only accumulates from when a player is registered; earlier matches are already gone upstream.
- A player who plays more than ~25 matches between polls will have gaps.
- Narrow filters can produce win rates over very few matches, so match counts are always returned alongside.