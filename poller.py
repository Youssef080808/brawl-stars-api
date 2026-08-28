import requests
from config import API_PROXY, API_KEY

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