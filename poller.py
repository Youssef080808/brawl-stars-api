import requests
from config import API_PROXY, API_KEY
import time
import db
import parser
# Test
# Fetches a player's profile: name, trophies, ranked elo, brawler stats
def fetch_player(tag):
    return _get(f"/players/{_encode(tag)}")

# Fetches a player's recent battles, last 25 
def fetch_battles(tag):
    return _get(f"/players/{_encode(tag)}/battlelog")


# Shared request logic: adds auth, checks for errors, returns parsed JSON
def _get(path):
    # GET Request
    response = requests.get(
        f"{API_PROXY}{path}", 
        headers={"Authorization": f"Bearer {API_KEY}"}, # Authentication using API Key
        timeout=10 # Give up after 10 seconds
        )
    response.raise_for_status() # Raises an exception if 4xx/5xx error occurs
    return response.json() # Retun parsed JSON(Python Objects)

# Player tags start with '#', which has to be percent-encoded in a URL
def _encode(tag):
    return tag.replace("#", "%23")

# Polls one player: stores a snapshot and any new battles.
# Returns how many battles were new.
def poll_player(tag):
    # Fetch and insert current player snapshot
    player_data = fetch_player(tag)
    db.insert_snapshot(tag, player_data)

    # Fetch and insert new player battles
    logs = fetch_battles(tag)
    rows = []
    for entry in logs.get("items", []):
        row = parser.parse_battle(tag, entry)
        if row is not None:   # parse_battle returns None for battles it can't handle
            rows.append(row)

    count = db.insert_battles(rows) # Number of new battles added
    db.mark_polled(tag) # Reset last_polled time for given player
    return count

# Polls every tracked player once. Pauses between players to stay under the
# upstream rate limit, and keeps going if one player fails.
def poll_all(delay=0.5):
    for player in db.get_tracked_players():
        tag = player["tag"]
        try:    # Catch exception if fetch fails
            count = poll_player(tag)
            print(f"{tag}: played {count} new battles")
        except Exception as e:
            print(f"{tag} failed : {e}")
        time.sleep(delay) # Apply delapy/pause between players

# Runs if file is run directly
if __name__ == "__main__":
    db.db_init()
    poll_all()

     


    
