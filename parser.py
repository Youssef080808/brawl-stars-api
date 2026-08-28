import json

# Finds a player's entry in a battle (3v3 has nested structre, Showdown has flat structre)
def _find_player(battle, tag):
    # Check for player in showdown
    for player in battle.get("players", []):
        if player["tag"] == tag:
            return player
    # Check for player in 3v3 teams
    for team in battle.get("teams", []):
        for player in team:
            if player["tag"] == tag:
                return player
    return None # Player not in match (Shouldn't occur)

# Outcomes based on Showdown Placement
_SHOWDOWN_RULES = {
    "soloShowdown" : {"win" : 4, "draw" : 5, "loss" : 6, "cap" : 10},#1-4=win,5=draw,6-10=loss
    "duoShowdown"  : {"win" : 2, "draw" : 3, "loss" : 4, "cap" : 5}, #1-2=win,3-draw,4-5=loss
    "trioShowdown" : {"win" : 2, "draw" : 3, "loss" : 4, "cap" : 4}  #1-2=win,3=draw,4=loss
}

# Converts battle into 'win'|'draw'|'loss' depending on game mode 
def _outcome(battle):
    # If mode is Showdown
    mode = battle.get("mode")
    if mode in _SHOWDOWN_RULES:
        rank = battle.get("rank")
        if rank is None:
            return None
        rules = _SHOWDOWN_RULES[mode]
        if rank <= rules["win"]:
            return "win"
        elif rank == rules["draw"]:
            return "draw"
        elif rank >= rules["loss"] and rank <= rules["cap"]:
            return "loss"
        else:
            return None
        
    # If mode is 3v3 
    result = battle.get("result")
    if result == "victory":
        return "win"
    elif result == "draw":
        return "draw"
    elif result == "defeat":
        return "loss"

    return None

# Checks if given player was the star player
def _star_player(battle, tag):
    star = battle.get("starPlayer")
    if star is None:
        return None
    return 1 if star.get("tag") == tag else 0

# Parses a battle entry into a Row that can be added to battles table
def parse_battle(tag, entry):
    battle = entry.get("battle", {})
    event = entry.get("event", {})

    outcome = _outcome(battle)
    if outcome is None: # If mode unknown or missing outcome data
        return None 

    player = _find_player(battle, tag)
    if player is None: # Player not in this battle
        return None

    was_star = _star_player(battle, tag)

    # Return Row based off battles table 
    return {
        "player_tag" : tag,
        "battle_time" : entry.get("battleTime"),
        "mode" : battle.get("mode"),
        "map" : event.get("map"),
        "type" : battle.get("type"),
        "brawler" : player["brawler"]["name"],
        "outcome" : outcome,
        "result" : battle.get("result"),
        "rank" : battle.get("rank"),
        "trophy_gain" : battle.get("trophyChange"),
        "star_player" : was_star,
        "duration" : battle.get("duration"),
        "json" : json.dumps(entry)
    }



    


