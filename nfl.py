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
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Sportradar API: {e}")
        return None

if __name__ == "__main__":
    schedule = get_current_week_schedule()
    if schedule:
        print(schedule)
