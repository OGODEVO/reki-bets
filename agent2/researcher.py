import os
import json
from datetime import datetime, date
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from openai import OpenAI
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# --- Configuration & Initialization ---
load_dotenv()

# Load system prompt
try:
    with open("agent2/system_prompt.txt", "r") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    SYSTEM_PROMPT = "You are a helpful research assistant." # Fallback
    print("Warning: agent2/system_prompt.txt not found. Using default system prompt.")

# Load API keys from environment
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_BASE_URL = os.getenv("XAI_BASE_URL")

if not BRAVE_API_KEY:
    raise ValueError("Brave Search API key not found. Please set BRAVE_API_KEY in .env")
if not XAI_API_KEY or not XAI_BASE_URL:
    raise ValueError("XAI API key or base URL not found. Please set XAI_API_KEY and XAI_BASE_URL in .env")

# --- Browser Tool ---
class BrowserTool:
    """
    A tool that allows an agent to search the web using the Brave Search API.
    """
    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str) -> List[Dict[str, Any]]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        params = {"q": query}
        response = requests.get(self.base_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("web", {}).get("results", [])

# Initialize clients
browser = BrowserTool()
xai_client = OpenAI(
    api_key=XAI_API_KEY,
    base_url=XAI_BASE_URL,
)

# Initialize FastAPI app
app = FastAPI()

# --- Data Storage ---
NEWS_DATA_FILE = "agent2_nba_news.json"
BETTING_NEWS_DATA_FILE = "agent2_betting_news.json"
RESEARCH_DATA_FILE = "agent2_research_data.json"

def save_json_data(data, filename):
    """Saves data to a specified JSON file."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# --- API Models ---
class ResearchRequest(BaseModel):
    query: str

# --- Core Logic ---
def process_with_llm(query: str, search_results: List[Dict[str, Any]]):
    """
    Uses the Grok model to process and summarize search results.
    """
    print("Processing results with Grok...")
    
    results_summary = "\n".join([f"- {item.get('title', 'No Title')}: {item.get('description', 'No description.')}" for item in search_results[:5]])

    # Inject current date into the system prompt
    formatted_prompt = SYSTEM_PROMPT.format(current_date=datetime.now().isoformat())

    user_prompt = f"""
    Original Query: "{query}"
    
    Search Results:
    {results_summary}
    
    Based on the search results, provide a clear, structured summary that directly answers the original query. Focus on facts and key data points.
    """

    response = xai_client.chat.completions.create(
        model="grok-4-fast-reasoning",
        messages=[
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content

@app.post("/research")
def perform_research(request: ResearchRequest):
    """
    API endpoint to perform a web search and process the results.
    """
    print(f"Received research request for: {request.query}")
    
    search_results = browser.search(request.query)
    
    if not search_results:
        raise HTTPException(status_code=404, detail="No search results found.")

    processed_summary = process_with_llm(request.query, search_results)
    
    final_data = {
        "query": request.query,
        "last_updated": datetime.now().isoformat(),
        "summary": processed_summary,
        "raw_results": search_results
    }
    save_json_data(final_data, RESEARCH_DATA_FILE)
    
    print("Research complete. Returning summary.")
    return {"summary": processed_summary}

# --- Web Scraping Logic ---
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
