import os
import requests
from cachetools import cached, TTLCache

# Cache for the daily schedule, expires every 12 hours
schedule_cache = TTLCache(maxsize=128, ttl=43200)

@cached(schedule_cache)
def get_daily_schedule(year: int, month: int, day: int):
    """
    Fetches the NBA daily schedule for a given date.
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        return {"status": "error", "error": "SPORTRADAR_API_KEY not found in environment variables."}

    url = f"https://api.sportradar.com/nba/production/v8/en/games/{year}/{month}/{day}/schedule.json"
    params = {"api_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"API request failed: {e}"}

def get_daily_injuries(year: int, month: int, day: int):
    """
    Fetches the NBA daily injuries for a given date.
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        return {"status": "error", "error": "SPORTRADAR_API_KEY not found in environment variables."}

    url = f"https://api.sportradar.com/nba/production/v8/en/league/{year}/{month}/{day}/daily_injuries.json"
    params = {"api_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"API request failed: {e}"}

def get_game_summary(game_id: str):
    """
    Fetches the game summary for a given game_id.
    """
    api_key = os.getenv("SPORTRADAR_API_KEY")
    if not api_key:
        return {"status": "error", "error": "SPORTRADAR_API_KEY not found in environment variables."}

    url = f"https://api.sportradar.com/nba/production/v8/en/games/{game_id}/summary.json"
    params = {"api_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"API request failed: {e}"}
