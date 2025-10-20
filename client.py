import os
import json
import requests
from typing import Dict, Any, Optional

class SportRadarClient:
    def __init__(self, api_key: str, base_url: str):
        if not api_key:
            raise ValueError("Sportradar API key is required.")
        if not base_url:
            raise ValueError("Base URL is required.")
            
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = 10

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes a request to the Sportradar API and handles errors."""
        if params is None:
            params = {}
        
        endpoint = endpoint.strip("/")
        url = f"{self.base_url}/{endpoint}"
        all_params = {"api_key": self.api_key, **params}

        try:
            response = requests.get(url, params=all_params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if "message" in data and "code" in data and data["code"] != 200:
                 raise requests.exceptions.HTTPError(f"API Error {data['code']}: {data['message']}")

            return data
        except requests.exceptions.RequestException as e:
            print(f"Error calling Sportradar API endpoint '{endpoint}': {e}")
            return {"status": "error", "message": str(e)}
        except json.JSONDecodeError:
            print(f"Error decoding JSON from Sportradar API endpoint '{endpoint}'")
            return {"status": "error", "message": "Invalid JSON response from API."}

SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY")

# Create and export sport-specific clients
nfl_client = SportRadarClient(api_key=SPORTRADAR_API_KEY, base_url="https://api.sportradar.com/nfl/official/production/v7/en")
nba_client = SportRadarClient(api_key=SPORTRADAR_API_KEY, base_url="https://api.sportradar.com/nba/production/v8/en")
odds_client = SportRadarClient(api_key=SPORTRADAR_API_KEY, base_url="https://api.sportradar.com/oddscomparison-prematch/production/v2/en")
