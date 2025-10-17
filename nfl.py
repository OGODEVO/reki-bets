import os
import requests
from dotenv import load_dotenv

load_dotenv()

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
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching schedule from Sportradar API: {e}")
        return None

def get_game_statistics(
    game_id: str,
    access_level: str = "trial",
    language_code: str = "en",
    version: str = "v7",
    file_format: str = "json",
) -> dict:
    """
    Retrieves the statistics for a specific NFL game from the Sportradar API.

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
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching game statistics from Sportradar API: {e}")
        return None

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
            # Print a small part of the stats to verify
            print("Summary:", stats.get("summary"))
    else:
        print("Could not fetch schedule or no games found in the current week.")