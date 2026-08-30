from fastapi import FastAPI, HTTPException, Query
import db

app = FastAPI(title="Brawl Stars stats API") # Create application object (map with routing table)

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
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="player not tracked")
    
    return dict(row)

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


