import sqlite3
from config import DB_PATH # Where DB file lives

# Creates and returns configured connection
def get_connection():
    conn = sqlite3.connect(DB_PATH) # Open DB files and creates it if it doesnt exist
    conn.row_factory = sqlite3.Row # Access colomns by name 
    return conn

# Creates all tables if they don't already exist. Safe to run freely
def db_init():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            tag         TEXT PRIMARY KEY, -- player tag
            name        TEXT NOT NULL,    -- in game name
            chat_id     TEXT,             -- sub's chat id,NULL if add player not via Telegram
            added_at    TEXT NOT NULL,    -- Time player started being tracked
            last_polled TEXT              -- Last time poller fetched this player
        )
    """)

    # Primary key player tag and battle time since one player can be only in one battle at a
    # given second. Also makes repolling safe 
    conn.execute("""
        CREATE TABLE IF NOT EXISTS battles (
            player_tag  TEXT NOT NULL,
            battle_time TEXT NOT NULL, -- From the API
            mode        TEXT NOT NULL, -- Ex: GemGrab, BrawlBall
            map         TEXT NOT NULL,
            type        TEXT NOT NULL, -- 'ranked' = trophies, 'soloRanked' = competitive
            brawler     TEXT NOT NULL,
            outcome     TEXT NOT NULL, -- 'win'|'draw'|'loss'
            result      TEXT,          -- 3v3 'victory'|'defeat'|'draw', NULL in showdown
            rank        INTEGER,       -- Showdown Placement, NULL if not Showdown
            trophy_gain INTEGER,       -- NULL for competivtive matches
            star_player INTEGER,       -- 1=starPlayer,0=not,NULL for showdown matches
            duration    INTEGER ,      -- Match duration in seconds, Showdown has no duration
            json        TEXT,          -- Saved during developement such as not to lose data
            PRIMARY KEY(player_tag, battle_time)

        )
    """)

    # Periodic trophy readings, for tracking progression over time.
    # Many readings per player, so keyed on (player_tag, taken_at).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            player_tag          TEXT NOT NULL,
            taken_at            TEXT NOT NULL,      -- When snapshot/reading was taken
            trophies            INTEGER NOT NULL,
            ranked_elo          INTEGER,
            rank_name           TEXT,
            ranked_season_id    INTEGER,
            rank                INTEGER,            -- Integer rank value 
            PRIMARY KEY(player_tag, taken_at)
        )
""")

    conn.commit() # Commit created tables
    conn.close()

# Runs db_init() when you run file directly
if __name__ == "__main__":
    db_init()
    print(f"Database inialised at {DB_PATH}")
