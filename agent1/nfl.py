import os
import uuid
from datetime import datetime
from cachetools import cached, TTLCache
from dotenv import load_dotenv

# Assuming sportradar_client is initialized in client.py and imported
from client import nfl_client as sportradar_client

load_dotenv()

NFL_TEAMS = {
    "San Francisco 49ers": "f0e724b0-4cbf-495a-be47-013907608da9",
    "Chicago Bears": "7b112545-38e6-483c-a55c-96cf6ee49cb8",
    "Cincinnati Bengals": "ad4ae08f-d808-42d5-a1e6-e9bc4e34d123",
    "Buffalo Bills": "768c92aa-75ff-4a43-bcc0-f2798c2e1724",
    "Denver Broncos": "ce92bd47-93d5-4fe9-ada4-0fc681e6caa0",
    "Cleveland Browns": "d5a2eb42-8065-4174-ab79-0a6fa820e35e",
    "Tampa Bay Buccaneers": "4254d319-1bc7-4f81-b4ab-b5e6f3402b69",
    "Arizona Cardinals": "de760528-1dc0-416a-a978-b510d20692ff",
    "Los Angeles Chargers": "1f6dcffb-9823-43cd-9ff4-e7a8466749b5",
    "Kansas City Chiefs": "6680d28d-d4d2-49f6-aace-5292d3ec02c2",
    "Indianapolis Colts": "82cf9565-6eb9-4f01-bdbd-5aa0d472fcd9",
    "Washington Commanders": "22052ff7-c065-42ee-bc8f-c4691c50e624",
    "Dallas Cowboys": "e627eec7-bbae-4fa4-8e73-8e1d6bc5c060",
    "Miami Dolphins": "4809ecb0-abd3-451d-9c4a-92a90b83ca06",
    "Philadelphia Eagles": "386bdbf9-9eea-4869-bb9a-274b0bc66e80",
    "Atlanta Falcons": "e6aa13a4-0055-48a9-bc41-be28dc106929",
    "New York Giants": "04aa1c9d-66da-489d-b16a-1dee3f2eec4d",
    "Jacksonville Jaguars": "f7ddd7fa-0bae-4f90-bc8e-669e4d6cf2de",
    "New York Jets": "5fee86ae-74ab-4bdd-8416-42a9dd9964f3",
    "Detroit Lions": "c5a59daa-53a7-4de0-851f-fb12be893e9e",
    "Green Bay Packers": "a20471b4-a8d9-40c7-95ad-90cc30e46932",
    "Carolina Panthers": "f14bf5cc-9a82-4a38-bc15-d39f75ed5314",
    "New England Patriots": "97354895-8c77-4fd4-a860-32e62ea7382a",
    "Las Vegas Raiders": "7d4fcc64-9cb5-4d1b-8e75-8a906d1e1576",
    "Los Angeles Rams": "2eff2a03-54d4-46ba-890e-2bc3925548f3",
    "Baltimore Ravens": "ebd87119-b331-4469-9ea6-d51fe3ce2f1c",
    "New Orleans Saints": "0d855753-ea21-4953-89f9-0e20aff9eb73",
    "Seattle Seahawks": "3d08af9e-c767-4f88-a7dc-b920c6d2b4a8",
    "Pittsburgh Steelers": "cb2f9f1f-ac67-424e-9e72-1475cb0ed398",
    "Team TBD": "23ed0bf0-f058-11ee-9989-93cc4251593a",
    "Houston Texans": "82d2d380-3834-4938-835f-aec541e5ece7",
    "Tennessee Titans": "d26a1ca5-722d-4274-8f97-c92e49c96315",
    "Minnesota Vikings": "33405046-04ee-4058-a950-d606f8c30852",
}

ABBREVIATIONS = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

TEAM_LOOKUP = {}
for full_name, team_id in NFL_TEAMS.items():
    TEAM_LOOKUP[full_name.lower()] = team_id
    mascot = full_name.split()[-1]
    TEAM_LOOKUP[mascot.lower()] = team_id
for abbr, full_name in ABBREVIATIONS.items():
    if full_name in NFL_TEAMS:
        TEAM_LOOKUP[abbr.lower()] = NFL_TEAMS[full_name]

# Cache for the weekly schedule, expires every 24 hours
schedule_cache = TTLCache(maxsize=10, ttl=86400)

@cached(schedule_cache)
def get_nfl_current_week_schedule() -> dict:
    """Retrieves the NFL schedule for the current week."""
    endpoint = "games/current_week/schedule.json"
    return sportradar_client._make_request(endpoint)

def find_nfl_game_by_teams_and_date(team1: str, team2: str, date: str) -> dict:
    """
    Finds a specific NFL game by team names and date.

    Args:
        team1: The name of the first team.
        team2: The name of the second team.
        date: The date of the game in YYYY-MM-DD format.

    Returns:
        A dictionary containing the game's information or an error.
    """
    try:
        game_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Please use YYYY-MM-DD."}

    schedule_data = get_nfl_current_week_schedule()
    if schedule_data.get("status") == "error":
        return schedule_data

    games = schedule_data.get("week", {}).get("games", [])
    
    team1_lower = team1.lower()
    team2_lower = team2.lower()

    for game in games:
        game_scheduled_dt = datetime.fromisoformat(game["scheduled"])
        if game_scheduled_dt.date() == game_date.date():
            home_team_name = game["home"]["name"].lower()
            away_team_name = game["away"]["name"].lower()
            
            if (team1_lower in home_team_name and team2_lower in away_team_name) or \
               (team2_lower in home_team_name and team1_lower in away_team_name):
                return {"status": "ok", "game": game}

    return {"status": "not_found", "message": f"No game found between {team1} and {team2} on {date}."}

def get_nfl_game_statistics(game_id: str) -> dict:
    """Retrieves statistics for a specific NFL game."""
    endpoint = f"games/{game_id}/statistics.json"
    return sportradar_client._make_request(endpoint)

def get_nfl_game_roster(game_id: str) -> dict:
    """Retrievels the roster for a specific NFL game."""
    endpoint = f"games/{game_id}/roster.json"
    return sportradar_client._make_request(endpoint)

def get_nfl_team_season_stats(
    team_identifier: str,
    season_year: str = "2025",
    season_type: str = "reg",
) -> dict:
    """Retrieves the seasonal statistics for a specific NFL team."""
    resolved_team_id = TEAM_LOOKUP.get(team_identifier.lower())
    if not resolved_team_id:
        try:
            uuid.UUID(team_identifier)
            resolved_team_id = team_identifier
        except ValueError:
            return {"status": "error", "message": f"Could not find a valid team ID for '{team_identifier}'"}

    endpoint = f"seasons/{season_year}/{season_type}/teams/{resolved_team_id}/statistics.json"
    return sportradar_client._make_request(endpoint)

if __name__ == "__main__":
    print("--- Fetching Current Week Schedule ---")
    schedule = get_nfl_current_week_schedule()
    if schedule.get("status") != "error":
        print("Successfully fetched schedule.")
        
        # Test the new find_game function
        if schedule.get("week", {}).get("games"):
            first_game = schedule["week"]["games"][0]
            home_team = first_game["home"]["name"]
            away_team = first_game["away"]["name"]
            game_date = datetime.fromisoformat(first_game["scheduled"]).strftime("%Y-%m-%d")

            print(f"\n--- Finding Game: {away_team} at {home_team} on {game_date} ---")
            found_game_info = find_nfl_game_by_teams_and_date(home_team, away_team, game_date)
            if found_game_info.get("status") == "ok":
                found_game = found_game_info["game"]
                print(f"Successfully found game with ID: {found_game['id']}")
                
                game_id = found_game['id']
                print(f"\n--- Fetching Statistics for Game ID: {game_id} ---")
                stats = get_nfl_game_statistics(game_id=game_id)
                if stats.get("status") != "error":
                    print("Successfully fetched game statistics.")
                else:
                    print(f"Error fetching stats: {stats.get('message')}")

                print(f"\n--- Fetching Roster for Game ID: {game_id} ---")
                roster = get_nfl_game_roster(game_id=game_id)
                if roster.get("status") != "error":
                    print("Successfully fetched game roster.")
                else:
                    print(f"Error fetching roster: {roster.get('message')}")
            else:
                print(f"Could not find game: {found_game_info.get('message')}")

        print(f"\n--- Fetching Team Season Stats (Testing Multiple Identifiers) ---")
        test_teams = ["Jacksonville Jaguars", "KC", "Ravens", "f0e724b0-4cbf-495a-be47-013907608da9"]
    
        for team_identifier in test_teams:
            print(f"\n--- Testing with identifier: '{team_identifier}' ---")
            season_stats = get_nfl_team_season_stats(team_identifier=team_identifier)
            if season_stats.get("status") != "error":
                print(f"Successfully fetched season stats for {team_identifier}.")
            else:
                print(f"Could not find season stats for '{team_identifier}': {season_stats.get('message')}")
    else:
        print(f"Could not fetch schedule: {schedule.get('message')}")
