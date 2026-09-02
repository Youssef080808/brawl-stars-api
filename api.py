from fastapi import FastAPI, HTTPException, Query
import db
from pydantic import BaseModel
import poller
import requests

app = FastAPI(title="Brawl Stars stats API") # Create application object (map with routing table)

db.db_init()

# Checks that whole stack is working
@app.get("/health")
def health():
    return {"status" : "ok"} # FastAPI converts dict to JSON automatically

# Returns tracking info for given player
@app.get("/players/{tag}")
def get_player(tag: str):
    tag = _normalise(tag)

    conn = db.get_connection()
    row = conn.execute(
        "SELECT tag, name, added_at, last_polled FROM players WHERE tag = ?", (tag,)
        ).fetchone()
    

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="player not tracked")
    
    # Most recent reading, or None if the player has never been polled
    snapshot = conn.execute("""
        SELECT taken_at, trophies, ranked_elo, rank_name, ranked_season_id, rank
        FROM snapshots
        WHERE player_tag = ?
        ORDER BY taken_at DESC
        LIMIT 1
    """, (tag,)).fetchone()

    conn.close()

    return {
        **dict(row),
        "latest": dict(snapshot) if snapshot else None,
    }

# Converts to correct form incase tag has no "#"
def _normalise(tag):
    tag = tag.upper()
    if not tag.startswith("#"):
        tag = "#" + tag
    return tag

# Win/draw/loss counts over a player's recent battles, with optional filters
@app.get("/players/{tag}/record")
def get_record(tag: str, last: int = Query(100, ge=1, le=1000), mode: str|None=None,
                map: str | None=None, type: str|None=None, brawler: str|None=None):
    tag = _normalise(tag)

    # Build the filter conditions from whichever parameters were supplied
    conditions = []
    params = []
    if mode:
        conditions.append("mode = ?")
        params.append(mode)
    if map:
        conditions.append("map = ?")
        params.append(map)
    if type:
        conditions.append("type = ?")
        params.append(type)
    if brawler:
        conditions.append("brawler = ?")
        params.append(brawler.upper())

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = db.get_connection()
    row  = conn.execute(f"""
        SELECT
            SUM(outcome = 'win') AS wins, -- SUM gives NULL if 0
            SUM(outcome = 'draw') AS draws, 
            SUM(outcome = 'loss') AS losses,
            COUNT(*) AS total -- gives 0 if 0

            FROM (
                SELECT * FROM battles
                WHERE player_tag = ?
                ORDER BY battle_time DESC
                LIMIT ?
            ){where}
""", [tag, last] + params).fetchone()
    conn.close()

    return {
        "wins" : row["wins"] or 0,
        "draws" : row["draws"] or 0,
        "losses" : row["losses"] or 0,
        "total" : row["total"]
    }

# Per brawler win/draw/loss breakdown over a player's recent battles
@app.get("/players/{tag}/brawlers")
def get_brawlers(tag: str, last: int = Query(100, ge=1, le=10000), 
                 top: int = Query(5, ge=1, le=20),
                 min_matches: int = Query(10, ge=1),
                 mode: str | None = None, map: str | None = None,
                 type: str | None = None 
                 ):
    tag = _normalise(tag)

    conditions = []
    params = []
    if mode:
        conditions.append("mode = ?")
        params.append(mode)
    if map:
        conditions.append("map = ?")
        params.append(map)
    if type:
        conditions.append("type = ?")
        params.append(type)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = db.get_connection()
    rows = conn.execute(f"""
        SELECT
            brawler,
            SUM(outcome = 'win')  AS wins,
            SUM(outcome = 'draw') AS draws,
            SUM(outcome = 'loss') AS losses,
            COUNT(*)              AS total
            FROM (
                SELECT * FROM battles
                WHERE player_tag = ?
                ORDER BY battle_time DESC
                LIMIT ?
            ){where}
            GROUP BY brawler
            HAVING total >= ?
            ORDER BY CAST(wins AS FLOAT) / total DESC, total DESC
            LIMIT ?
""", [tag, last] + params + [min_matches, top]).fetchall()
    conn.close()

    return [dict(row) for row in rows]

# Trophy and ranked history for a player, most recent first
@app.get("/players/{tag}/trophies")
def get_trophies(tag: str, limit: int = Query(50, ge=1, le=1000)):
    tag = _normalise(tag)

    conn = db.get_connection()
    rows = conn.execute("""
        SELECT taken_at, trophies, ranked_elo, rank_name, ranked_season_id, rank
        FROM snapshots WHERE player_tag = ?
        ORDER BY taken_at DESC
        LIMIT ?  
    """, (tag, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Stored battles for a player, most recent first
@app.get("/players/{tag}/battles")
def get_battles(tag: str, limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0)):
    tag = _normalise(tag)

    conn = db.get_connection()
    rows = conn.execute("""
        SELECT battle_time, mode, map, type, brawler, outcome,
               rank, trophy_gain, star_player, duration
        FROM battles WHERE player_tag = ?
        ORDER BY battle_time DESC
        LIMIT ? OFFSET ? -- Offset used to pull through a long history without pulling all
                         -- at once
    """, (tag, limit, offset)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Shape of the POST /players request body. FastAPI validates incoming JSON
# against this and returns a 422 if it doesn't match.
class PlayerRegistration(BaseModel):
    tag: str
    chat_id: str | None = None

# Registers a player for tracking. Checks the tag exists upstream first, so a
# typo doesn't create a row the poller then fails on every cycle.
@app.post("/players", status_code=201)
def register_player(body: PlayerRegistration):
    tag = _normalise(body.tag)

    try:
        player_data = poller.fetch_player(tag)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="no such player")
        raise HTTPException(status_code=502, detail="upstream API unavailable")
    
    db.add_player(tag, player_data.get("name"), body.chat_id)
    return {"tag": tag, "name": player_data.get("name")}

@app.delete("/players/{tag}", status_code=204)
def unsubscribe_player(tag: str):
    tag = _normalise(tag)
    db.remove_player(tag)


