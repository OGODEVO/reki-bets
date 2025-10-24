import requests
import time
from datetime import datetime
import pytz

# --- Configuration ---
BASE_URL = "http://localhost:8007"
NEWS_ENDPOINT = f"{BASE_URL}/news"
BETTING_NEWS_ENDPOINT = f"{BASE_URL}/betting-news"
TARGET_TIMEZONE = "America/Chicago"
TARGET_HOUR = 10
TARGET_MINUTE = 56

# --- Job Definition ---
def run_daily_research():
    """
    Triggers the data gathering endpoints on the research service.
    """
    print(f"[{datetime.now(pytz.timezone(TARGET_TIMEZONE))}] Triggering daily research tasks...")
    
    try:
        # 1. Fetch general NBA News
        print("Requesting general NBA news...")
        response_news = requests.post(NEWS_ENDPOINT)
        response_news.raise_for_status()
        print(f"News request successful: {response_news.status_code}")

        # 2. Fetch Betting News
        print("Requesting betting news...")
        response_betting = requests.post(BETTING_NEWS_ENDPOINT)
        response_betting.raise_for_status()
        print(f"Betting news request successful: {response_betting.status_code}")

        print("All research tasks completed successfully.")

    except requests.RequestException as e:
        print(f"An error occurred during a request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Main Scheduling Loop ---
def main():
    """
    Main loop to check the time and run the job at the target time in the specified timezone.
    """
    tz = pytz.timezone(TARGET_TIMEZONE)
    last_run_date = None
    
    print(f"Scheduler started. Will run tasks daily at {TARGET_HOUR:02d}:{TARGET_MINUTE:02d} {TARGET_TIMEZONE} time.")
    print("To stop, press Ctrl+C")

    while True:
        now_in_tz = datetime.now(tz)
        
        # Check if it's the target time and if the job hasn't run today.
        if (now_in_tz.hour == TARGET_HOUR and 
            now_in_tz.minute == TARGET_MINUTE and 
            now_in_tz.date() != last_run_date):
            
            run_daily_research()
            last_run_date = now_in_tz.date()
        
        # Sleep for 60 seconds before the next check.
        time.sleep(60)

if __name__ == "__main__":
    main()