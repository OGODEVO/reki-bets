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
    with open("system_prompt.txt", "r") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    SYSTEM_PROMPT = "You are a helpful research assistant." # Fallback
    print("Warning: system_prompt.txt not found. Using default system prompt.")

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
    print(f"[{datetime.now()}] Received research request for: {request.query}")
    
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
    
    print(f"[{datetime.now()}] Research complete for query: '{request.query}'. Returning summary.")
    return {"summary": processed_summary}

# --- Web Scraping & Summarization Logic ---
def summarize_with_llm(text: str, max_chars: int = 4000):
    """
    Summarizes a given text using the Grok model.
    """
    if not text:
        return "No content available to summarize."
    
    # Truncate text to avoid exceeding model context limits
    truncated_text = text[:max_chars]

    prompt = f"""
    Please summarize the following article text in 2-3 concise sentences. Focus on the key takeaways and most important information.
    
    Article Text:
    "{truncated_text}"
    """
    try:
        response = xai_client.chat.completions.create(
            model="grok-4-fast-reasoning",
            messages=[
                {"role": "system", "content": "You are an expert at summarizing sports news articles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Failed to generate summary."

def fetch_and_summarize(url: str, link_selector: str, article_selector: str, base_url: str = ""):
    """
    Generic function to fetch links, visit each page, and summarize its content.
    """
    print(f"Fetching news from: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching main URL {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    links = soup.select(link_selector)
    summarized_articles = []

    for title_element in links[:5]: # Limit to 5 articles to manage processing time
        try:
            link = title_element.find_parent('a')
            if not link:
                continue

            article_url = link.get('href')
            if not article_url or not article_url.startswith('/news/'):
                continue
                
            article_url = base_url + article_url
            
            title = title_element.text.strip()

            print(f"  - Visiting: {article_url}")
            article_response = requests.get(article_url, headers={'User-Agent': 'Mozilla/5.0'})
            article_response.raise_for_status()
            
            article_soup = BeautifulSoup(article_response.content, 'html.parser')
            article_container = article_soup.find('main')
            
            if article_container:
                article_text = article_container.get_text(separator=' ', strip=True)
            else:
                article_text = ""

            summary = summarize_with_llm(article_text)

            if title and not any(d.get('link') == article_url for d in summarized_articles):
                 summarized_articles.append({"title": title, "link": article_url, "summary": summary})

        except requests.RequestException as e:
            print(f"  - Failed to fetch article {article_url}: {e}")
            continue
        except Exception as e:
            print(f"  - Error processing article {article_url}: {e}")
            continue
            
    return summarized_articles

@app.post("/news")
def get_news():
    """
    API endpoint to fetch and summarize the latest NBA news.
    """
    print(f"[{datetime.now()}] Received news request.")
    
    articles = fetch_and_summarize(
        url="https://www.nba.com/news/category/top-stories",
        link_selector="a[href^='/news/'] h4",
        article_selector="main > div", # Corrected selector for article content
        base_url="https://www.nba.com"
    )

    if not articles:
        raise HTTPException(status_code=404, detail="No news found or failed to parse news data.")

    final_data = {
        "last_updated": datetime.now().isoformat(),
        "articles": articles
    }
    save_json_data(final_data, NEWS_DATA_FILE)

    print(f"[{datetime.now()}] Successfully fetched and summarized news.")
    return final_data

@app.post("/betting-news")
def get_betting_news():
    """
    API endpoint to fetch and summarize the latest NBA betting news.
    """
    print(f"[{datetime.now()}] Received betting news request.")

    articles = fetch_and_summarize(
        url="https://www.bettingnews.com/nba/",
        link_selector="div.news-item h3 a",
        article_selector="div.news-content" # A guess for the article content container
    )

    if not articles:
        raise HTTPException(status_code=404, detail="No betting news found or failed to parse data.")

    final_data = {
        "last_updated": datetime.now().isoformat(),
        "articles": articles
    }
    save_json_data(final_data, BETTING_NEWS_DATA_FILE)

    print(f"[{datetime.now()}] Successfully fetched and summarized betting news.")
    return final_data

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Agent 2: Web Research Service...")
    uvicorn.run(app, host="0.0.0.0", port=8007)
