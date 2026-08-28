import os

# Supercell API key (BRAWL_API_KEY) read from the environment
API_KEY = os.environ.get("BRAWL_API_KEY")

# RoyaleAPI proxy, so a changing server IP doesn't break the whitelisted key
API_PROXY = "https://bsproxy.royaleapi.dev/v1"

# Where the database lives
DATA_DIR = os.environ.get("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "brawl.db")
