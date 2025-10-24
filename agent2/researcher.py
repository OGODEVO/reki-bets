import os
import json
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from openai import OpenAI
from brave_search import BraveSearch
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# --- Configuration & Initialization ---
load_dotenv()

# Load API keys from environment
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_BASE_URL = os.getenv("XAI_BASE_URL")

if not BRAVE_API_KEY:
    raise ValueError("Brave Search API key not found. Please set BRAVE_API_KEY in .env")
if not XAI_API_KEY or not XAI_BASE_URL:
    raise ValueError("XAI API key or base URL not found. Please set XAI_API_KEY and XAI_BASE_URL in .env")

# Initialize clients
brave_client = BraveSearch(api_key=BRAVE_API_KEY)
xai_client = OpenAI(
    api_key=XAI_API_KEY,
    base_url=XAI_BASE_URL,
)

# Initialize FastAPI app
app = FastAPI()

# --- Data Storage ---
SCHEDULE_DATA_FILE = "agent2_nba_schedule.json"
NEWS_DATA_FILE = "agent2_nba_news.json"
BETTING_NEWS_DATA_FILE = "agent2_betting_news.json"

def save_json_data(data, filename):
    """Saves data to a specified JSON file."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# --- API Models ---
class ResearchRequest(BaseModel):
    query: str

class ScheduleRequest(BaseModel):
    game_date: date = None # Expects YYYY-MM-DD format

# --- Web Scraping Logic ---
def fetch_nba_schedule(game_date: date):
    """
    Fetches the NBA schedule from nba.com for a given date.
    """
    date_str = game_date.strftime("%Y-%m-%d")
    url = f"https://www.nba.com/games?date={date_str}"
    print(f"Fetching schedule from: {url}")

    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch NBA schedule data.")

    soup = BeautifulSoup(response.content, 'html.parser')
    games = []
    game_cards = soup.find_all("div", class_="GameCard_gc__3_16k") 

    for card in game_cards:
        try:
            teams = card.find_all("span", class_="MatchupCardTeamName_teamName__3i-sP")
            if len(teams) == 2:
                away_team = teams[0].text.strip()
                home_team = teams[1].text.strip()
                games.append({"away_team": away_team, "home_team": home_team})
        except Exception as e:
            print(f"Error parsing a game card: {e}")
            continue

    return games

def fetch_nba_news():
    """
    Fetches the top news stories from nba.com/news.
    """
    url = "https://www.nba.com/news/category/top-stories"
    print(f"Fetching news from: {url}")

    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch NBA news data.")

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    news_items = soup.find_all("a", class_="Article_articleLink__2d20x")

    for item in news_items:
        try:
            title = item.find("h2").text.strip()
            link = "https://www.nba.com" + item['href']
            articles.append({"title": title, "link": link})
        except Exception as e:
            print(f"Error parsing a news item: {e}")
            continue
    
    return articles

def fetch_betting_news():
    """
    Fetches the latest NBA betting news from bettingnews.com.
    """
    url = "https://www.bettingnews.com/nba/"
    print(f"Fetching betting news from: {url}")

    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch betting news data.")

    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    # This selector is a guess and will need to be verified.
    news_items = soup.find_all("div", class_="news-item") 

    for item in news_items:
        try:
            title_element = item.find("h3")
            link_element = item.find("a")
            if title_element and link_element:
                title = title_element.text.strip()
                link = link_element['href']
                articles.append({"title": title, "link": link})
        except Exception as e:
            print(f"Error parsing a betting news item: {e}")
            continue
    
    return articles

@app.post("/schedule")
def get_schedule(request: ScheduleRequest):
    """
    API endpoint to fetch the NBA schedule for a specific date.
    """
    game_date = request.game_date if request.game_date else date.today()
    print(f"Received schedule request for: {game_date}")
    
    schedule_data = fetch_nba_schedule(game_date)
    
    if not schedule_data:
        raise HTTPException(status_code=404, detail="No games found or failed to parse schedule for the given date.")

    final_data = {
        "date": game_date.isoformat(),
        "last_updated": datetime.now().isoformat(),
        "games": schedule_data
    }
    save_json_data(final_data, SCHEDULE_DATA_FILE)
    
    print(f"Successfully fetched and saved schedule for {game_date}.")
    return final_data

@app.post("/news")
def get_news():
    """
    API endpoint to fetch the latest NBA news.
    """
    print("Received news request.")
    news_data = fetch_nba_news()

    if not news_data:
        raise HTTPException(status_code=404, detail="No news found or failed to parse news data.")

    final_data = {
        "last_updated": datetime.now().isoformat(),
        "articles": news_data
    }
    save_json_data(final_data, NEWS_DATA_FILE)

    print("Successfully fetched and saved news.")
    return final_data

@app.post("/betting-news")
def get_betting_news():
    """
    API endpoint to fetch the latest NBA betting news.
    """
    print("Received betting news request.")
    news_data = fetch_betting_news()

    if not news_data:
        raise HTTPException(status_code=404, detail="No betting news found or failed to parse data.")

    final_data = {
        "last_updated": datetime.now().isoformat(),
        "articles": news_data
    }
    save_json_data(final_data, BETTING_NEWS_DATA_FILE)

    print("Successfully fetched and saved betting news.")
    return final_data

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Agent 2: Web Research Service...")
    uvicorn.run(app, host="0.0.0.0", port=8007)
