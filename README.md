# Brawl Stars Stats API

A REST API that tracks Brawl Stars players over time.

Supercell's API only returns a snapshot: current trophies, and roughly the last 25 battles before the log rolls over. This service polls on a schedule and stores what it sees, so it can answer questions the official API can't — win rates over longer windows, per-brawler performance filtered by map and mode, and trophy progression over time.

Built to be used by a [Telegram bot](https://github.com/Youssef080808/Telegram-py-bot), but usable on its own.

**Status:** deployed and running on AWS EC2, polling every 30 minutes.

## Endpoints

```
GET    /health                   Liveness check
GET    /players/{tag}            Tracking info and latest snapshot
GET    /players/{tag}/record     Win/draw/loss counts, filtered
GET    /players/{tag}/brawlers   Per-brawler breakdown, ranked
GET    /players/{tag}/trophies   Trophy and ranked elo history
GET    /players/{tag}/battles    Stored battles, paginated
POST   /players                  Register a player for tracking
DELETE /players/{tag}            Stop tracking
```

`POST /players` verifies the tag against the upstream API before storing it, so a typo doesn't create a row the poller then fails on every cycle. A 404 upstream is passed through as a 404; anything else becomes a 502, since the failure is a dependency's rather than this service's.

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

## Deployment

Every push to `main` builds the image, publishes it to GitHub Container Registry, and redeploys the running container via AWS Systems Manager — no SSH keys in CI and no inbound ports opened.

The instance itself is provisioned by the [Telegram bot repository's Terraform](https://github.com/Youssef080808/Telegram-py-bot), since both services share one host. Its `user_data` script creates this service's data directory and token file, starts the container, and installs the poller's cron entry, so a fresh instance comes up with both services running.

Two containers run from the same image:

```bash
# The API, long-running
docker run -d --name brawl-api --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  --env-file /etc/brawl-api.env \
  -v /home/ec2-user/brawl-data:/data \
  ghcr.io/youssef080808/brawl-api:latest

# The poller, run by cron every 30 minutes and removed when it exits
docker run --rm \
  --env-file /etc/brawl-api.env \
  -v /home/ec2-user/brawl-data:/data \
  ghcr.io/youssef080808/brawl-api:latest python3 poller.py
```

The image's default command is the API; the poller overrides it. Both mount the same host directory, which is how they share a database despite being separate containers.

The API key is read from a root-only file written at provisioning time rather than passed on the command line, so it never appears in shell history, workflow definitions, or SSM command logs.

The port is bound to `127.0.0.1` rather than all interfaces, so the API is reachable only from the instance itself. Nothing is exposed publicly and no inbound firewall rule was needed — the only consumer is a bot running on the same host. Making it public would mean a reverse proxy, TLS, and rate limiting, which isn't warranted for a single internal caller.

## Project structure

- `config.py` — settings and secrets, read from the environment
- `db.py` — schema, connection helper, and storage functions
- `poller.py` — fetches from the upstream API and stores results
- `parser.py` — turns raw battle JSON into rows
- `api.py` — HTTP endpoints
- `Dockerfile` — the image both containers run from
- `.github/workflows/build.yml` — builds and publishes on every push to `main`

## Known limitations

- History only accumulates from when a player is registered; earlier matches are already gone upstream.
- A player who plays more than ~25 matches between polls will have gaps.
- A poll that fails partway leaves a snapshot written but no battles, since the two are stored separately.
- Narrow filters can produce records over very few matches, so counts are always returned alongside.
- Stored data lives on the instance's root volume, so replacing the instance means copying the database across by hand.
