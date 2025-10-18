import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY")

def get_daily_schedule_odds(sport_id: str, date: str):
    """
    Fetches the daily schedule odds for a given sport ID and date.
    """
    if not SPORTRADAR_API_KEY:
        return "Sportradar API key not found."

    url = f"https://api.sportradar.com/oddscomparison-prematch/trial/v2/en/sports/{sport_id}/schedules/{date}/schedules.json?api_key={SPORTRADAR_API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error fetching data: {e}"
