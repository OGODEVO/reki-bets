import os
import requests
import json
from datetime import datetime, timedelta
from cachetools import cached, TTLCache
from dotenv import load_dotenv

load_dotenv()
SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY")

SPORT_IDS = {
    "basketball": "sr:sport:2",
    "american_football": "sr:sport:16"
}

# Cache for the daily odds schedule, expires every hour
odds_cache = TTLCache(maxsize=256, ttl=3600)

@cached(odds_cache)
def get_daily_schedule_odds(sport_name: str, date: str):
    """
    Fetches the daily schedule for a given sport, returning a list of scheduled events
    and their unique sport_event_id, which is required to fetch market odds.
    """
    if not SPORTRADAR_API_KEY:
        return {"status": "error", "error": "Sportradar API key not found."}

    sport_id = SPORT_IDS.get(sport_name.lower())
    if not sport_id:
        return {"status": "error", "error": f"Invalid sport name: {sport_name}. Valid options are: {list(SPORT_IDS.keys())}"}

    url = f"https://api.sportradar.com/oddscomparison-prematch/trial/v2/en/sports/{sport_id}/schedules/{date}/schedules.json?api_key={SPORTRADAR_API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return {"status": "ok", "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Error fetching data: {e}"}

def get_sport_event_markets(
    sport_event_id: str,
    access_level: str = "trial",
    language_code: str = "en",
    file_format: str = "json",
):
    """
    Fetches and filters the available pre-match markets (moneyline, spread, total) for a specific sport event,
    returning only essential fields.
    """
    if not SPORTRADAR_API_KEY:
        return {"status": "error", "error": "Sportradar API key not found."}

    url = f"https://api.sportradar.com/oddscomparison-prematch/{access_level}/v2/{language_code}/sport_events/{sport_event_id}/sport_event_markets.{file_format}?api_key={SPORTRADAR_API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        all_markets_data = response.json()
        
        if "markets" not in all_markets_data:
            return {"status": "ok", "data": all_markets_data}

        target_markets = ["moneyline", "spread", "total"]
        
        filtered_markets = [
            market for market in all_markets_data["markets"]
            if any(target in market["name"].lower() for target in target_markets)
        ]
        
        # Further streamline the output to keep only essential fields
        for market in filtered_markets:
            market["books"] = [
                {
                    "name": book["name"],
                    "outcomes": [
                        {
                            "type": o.get("type"),
                            "odds_decimal": o.get("odds_decimal"),
                            "odds_american": o.get("odds_american"),
                            "total": o.get("total")
                        } for o in book.get("outcomes", [])
                    ]
                }
                for book in market.get("books", [])
            ]

        all_markets_data["markets"] = filtered_markets
        return {"status": "ok", "data": all_markets_data}
        
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Error fetching data: {e}"}

if __name__ == "__main__":
    # Get tomorrow's date for the schedule
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"--- Fetching Daily Schedule Odds for Basketball on {tomorrow_date} ---")
    schedule_data = get_daily_schedule_odds("basketball", tomorrow_date)
    
    if schedule_data and "sport_events" in schedule_data:
        sport_events = schedule_data["sport_events"]
        if sport_events:
            first_event_id = sport_events[0]["id"]
            print(f"Successfully fetched schedule. Found event with ID: {first_event_id}")
            
            print(f"\n--- Fetching Markets for Event ID: {first_event_id} ---")
            markets_data = get_sport_event_markets(first_event_id)
            
            if markets_data and "markets" in markets_data:
                print("Successfully fetched markets for the event.")
                # Print the first 3 market names to verify
                market_names = [market["name"] for market in markets_data["markets"][:3]]
                print("Available Markets (sample):", market_names)
            else:
                print("Could not fetch markets or no markets found for the event.")
        else:
            print("No sport events found in the schedule for tomorrow.")
    else:
        print("Could not fetch the daily schedule.")
