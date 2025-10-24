import requests
import schedule
import time
from datetime import date

# --- Configuration ---
BASE_URL = "http://localhost:8007"
SCHEDULE_ENDPOINT = f"{BASE_URL}/schedule"
NEWS_ENDPOINT = f"{BASE_URL}/news"
BETTING_NEWS_ENDPOINT = f"{BASE_URL}/betting-news"

# --- Job Definition ---
def run_daily_research():
    """
    Triggers all the data gathering endpoints on the research service.
    """
    print("Scheduler triggered. Running daily research tasks...")
    
    today = date.today().isoformat()
    
    try:
        # 1. Fetch NBA Schedule for today
        print(f"Requesting schedule for {today}...")
        response_schedule = requests.post(SCHEDULE_ENDPOINT, json={"game_date": today})
        response_schedule.raise_for_status()
        print(f"Schedule request successful: {response_schedule.status_code}")

        # 2. Fetch general NBA News
        print("Requesting general NBA news...")
        response_news = requests.post(NEWS_ENDPOINT)
        response_news.raise_for_status()
        print(f"News request successful: {response_news.status_code}")

        # 3. Fetch Betting News
        print("Requesting betting news...")
        response_betting = requests.post(BETTING_NEWS_ENDPOINT)
        response_betting.raise_for_status()
        print(f"Betting news request successful: {response_betting.status_code}")

        print("All research tasks completed successfully.")

    except requests.RequestException as e:
        print(f"An error occurred during a request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Scheduling ---
# Set the job to run every day at 10:45 AM.
# The time is in the local timezone of the machine running the script.
schedule.every().day.at("10:45").do(run_daily_research)

print("Scheduler started. Waiting for the scheduled time (10:45)...")
print("To stop, press Ctrl+C")

# --- Main Loop ---
while True:
    schedule.run_pending()
    time.sleep(1)
