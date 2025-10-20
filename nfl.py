import os
import uuid
import requests
from dotenv import load_dotenv

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

def get_current_week_schedule(
    access_level: str = "trial",
    language_code: str = "en",
    version: str = "v7",
    file_format: str = "json",
) -> dict:
    """
    Retrieves the NFL schedule for the current week from the Sportradar API.

    Args:
        access_level: The API access level.
        language_code: The language code for the response.
        version: The API version.
        file_format: The response format.

    Returns:
        A dictionary containing the current week's schedule information.
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        raise ValueError("SPORTRADAR_API_KEY not found in environment variables.")

    url = f"https://api.sportradar.com/nfl/official/{access_level}/{version}/{language_code}/games/current_week/schedule.{file_format}"
    params = {"api_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching schedule from Sportradar API: {e}")
        return {"status": "error", "error": str(e)}

def get_game_statistics(
    game_id: str,
    access_level: str = "trial",
    language_code: str = "en",
    version: str = "v7",
    file_format: str = "json",
) -> dict:
    """
    Retrieves statistics for a specific NFL game, including live, in-progress games.

    To get the game_id for a specific game, use the `get_current_week_schedule` function.

    Args:
        game_id: The unique identifier for the game.
        access_level: The API access level.
        language_code: The language code for the response.
        version: The API version.
        file_format: The response format.

    Returns:
        A dictionary containing the game's statistics.
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        raise ValueError("SPORTRADAR_API_KEY not found in environment variables.")

    url = f"https://api.sportradar.com/nfl/official/{access_level}/{version}/{language_code}/games/{game_id}/statistics.{file_format}"
    params = {"api_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game statistics from Sportradar API: {e}")
        return {"status": "error", "error": str(e)}

def get_game_roster(
    game_id: str,
    access_level: str = "trial",
    language_code: str = "en",
    version: str = "v7",
    file_format: str = "json",
) -> dict:
    """
    Retrieves the roster for a specific NFL game from the Sportradar API.

    Args:
        game_id: The unique identifier for the game.
        access_level: The API access level.
        language_code: The language code for the response.
        version: The API version.
        file_format: The response format.

    Returns:
        A dictionary containing the game's roster.
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        raise ValueError("SPORTRADAR_API_KEY not found in environment variables.")

    url = f"https://api.sportradar.com/nfl/official/{access_level}/{version}/{language_code}/games/{game_id}/roster.{file_format}"
    params = {"api_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game roster from Sportradar API: {e}")
        return {"status": "error", "error": str(e)}

def get_team_season_stats(
    team_identifier: str,
    season_year: str = "2025",
    season_type: str = "reg",
    access_level: str = "trial",
    language_code: str = "en",
    version: str = "v7",
    file_format: str = "json",
) -> dict:
    """
    Retrieves the seasonal statistics for a specific NFL team from the Sportradar API.

    Args:
        team_identifier: The name, abbreviation, or unique identifier for the team.
        season_year: The year of the season.
        season_type: The type of season (e.g., REG, PRE, PST).
        access_level: The API access level.
        language_code: The language code for the response.
        version: The API version.
        file_format: The response format.

    Returns:
        A dictionary containing the team's seasonal statistics.
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        raise ValueError("SPORTRADAR_API_KEY not found in environment variables.")

    resolved_team_id = None
    try:
        # Check if the identifier is a valid UUID
        uuid.UUID(team_identifier)
        resolved_team_id = team_identifier
    except ValueError:
        # If not a UUID, look it up in our dictionary
        resolved_team_id = TEAM_LOOKUP.get(team_identifier.lower())

    if not resolved_team_id:
        error_msg = f"Error: Could not find a valid team ID for '{team_identifier}'"
        print(error_msg)
        return {"status": "error", "error": error_msg}

    url = f"https://api.sportradar.com/nfl/official/{access_level}/{version}/{language_code}/seasons/{season_year}/{season_type}/teams/{resolved_team_id}/statistics.{file_format}"
    params = {"api_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching team season stats from Sportradar API: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("--- Fetching Current Week Schedule ---")
    schedule = get_current_week_schedule()
    if schedule and schedule.get("games"):
        first_game_id = schedule["games"][0]["id"]
        print(f"Successfully fetched schedule. Found game with ID: {first_game_id}")
        
        print(f"\n--- Fetching Statistics for Game ID: {first_game_id} ---")
        stats = get_game_statistics(game_id=first_game_id)
        if stats:
            print("Successfully fetched game statistics.")
            print("Summary:", stats.get("summary"))

        print(f"\n--- Fetching Roster for Game ID: {first_game_id} ---")
        roster = get_game_roster(game_id=first_game_id)
        if roster:
            print("Successfully fetched game roster.")
            print("Home Team Roster Size:", len(roster.get("home", {}).get("players", [])))
            print("Away Team Roster Size:", len(roster.get("away", {}).get("players", [])))
        
        print(f"\n--- Fetching Team Season Stats (Testing Multiple Identifiers) ---")
        test_teams = ["Jacksonville Jaguars", "KC", "Ravens", "f0e724b0-4cbf-495a-be47-013907608da9"] # Full name, abbreviation, mascot, UUID
    
        for team_identifier in test_teams:
            print(f"\n--- Testing with identifier: '{team_identifier}' ---")
            season_stats = get_team_season_stats(team_identifier=team_identifier)
            if season_stats:
                print(f"Successfully fetched season stats.")
                print("Record:", season_stats.get("record"))
            else:
                print(f"Could not find season stats for '{team_identifier}'.")

    else:
        print("Could not fetch schedule or no games found in the current week.")
