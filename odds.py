import os
from datetime import datetime, timedelta
from cachetools import cached, TTLCache
from dotenv import load_dotenv
from client import odds_client

load_dotenv()

SPORT_IDS = {
    "basketball": "sr:sport:2",
    "american_football": "sr:sport:16"
}

# Cache for the daily odds schedule, expires every hour
odds_cache = TTLCache(maxsize=256, ttl=3600)

@cached(odds_cache)
def get_daily_schedule_odds(sport_name: str, date: str) -> dict:
    """
    Fetches the daily schedule for a given sport, returning a list of scheduled events
    and their unique sport_event_id, which is required to fetch market odds.
    """
    sport_id = SPORT_IDS.get(sport_name.lower())
    if not sport_id:
        return {"status": "error", "message": f"Invalid sport name: {sport_name}. Valid options are: {list(SPORT_IDS.keys())}"}

    endpoint = f"sports/{sport_id}/schedules/{date}/schedules.json"
    return odds_client._make_request(endpoint)

def get_sport_event_markets(sport_event_id: str) -> dict:
    """
    Fetches and filters the available pre-match markets (moneyline, spread, total) for a specific sport event,
    returning only essential fields.
    """
    endpoint = f"sport_events/{sport_event_id}/sport_event_markets.json"
    all_markets_data = odds_client._make_request(endpoint)

    if all_markets_data.get("status") == "error" or "markets" not in all_markets_data:
        return all_markets_data

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

if __name__ == "__main__":
    # Get tomorrow's date for the schedule
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"--- Fetching Daily Schedule Odds for Basketball on {tomorrow_date} ---")
    schedule_response = get_daily_schedule_odds("basketball", tomorrow_date)
    
    if schedule_response.get("status") != "error":
        schedule_data = schedule_response.get('data', {})
        sport_events = schedule_data.get("sport_events", [])
        if sport_events:
            first_event_id = sport_events[0]["id"]
            print(f"Successfully fetched schedule. Found event with ID: {first_event_id}")
            
            print(f"\n--- Fetching Markets for Event ID: {first_event_id} ---")
            markets_response = get_sport_event_markets(first_event_id)
            
            if markets_response.get("status") != "error":
                markets_data = markets_response.get('data', {})
                print("Successfully fetched markets for the event.")
                # Print the first 3 market names to verify
                market_names = [market["name"] for market in markets_data.get("markets", [])[:3]]
                print("Available Markets (sample):", market_names)
            else:
                print(f"Could not fetch markets: {markets_response.get('message')}")
        else:
            print("No sport events found in the schedule for tomorrow.")
    else:
        print(f"Could not fetch the daily schedule: {schedule_response.get('message')}")
