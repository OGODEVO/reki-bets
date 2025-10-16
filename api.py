import os
import json
import time
import uuid
import requests
import serpapi
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Environment Setup ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

if not all([GEMINI_API_KEY, BRAVE_API_KEY, SPORTRADAR_API_KEY, SERPAPI_API_KEY]):
    raise ValueError("All API keys (GEMINI, BRAVE, SPORTRADAR, SERPAPI) must be set in .env file")

# --- Tool Definitions & Schema ---

def brave_search(query: str) -> str:
    """Performs a web search using the Brave Search API."""
    print(f"Performing Brave search for: {query}")
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
    params = {"q": query}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        results = response.json()
        simplified_results = [
            {"title": item.get("title"), "url": item.get("url"), "snippet": item.get("description")}
            for item in results.get("web", {}).get("results", [])[:3]
        ]
        return json.dumps(simplified_results)
    except Exception as e:
        return f"Error during search: {e}"

def get_soccer_summary_by_date(date: str) -> str:
    """
    Fetches a summary of soccer matches for a given date using the Sportradar Daily Summaries endpoint.
    """
    print(f"Getting Sportradar daily summary for: {date}")
    url = f"https://api.sportradar.com/soccer/v4/en/schedules/{date}/summaries.json"
    params = {"api_key": SPORTRADAR_API_KEY}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        summaries = response.json().get("summaries", [])
        
        simplified_summaries = []
        for item in summaries[:20]:
            context = item.get('sport_event_context', {})
            competition = context.get('competition', {})
            sport_event = item.get('sport_event', {})
            status = item.get('sport_event_status', {})
            
            simplified_summaries.append({
                "country": context.get('category', {}).get('name'),
                "tournament": competition.get('name'),
                "gender": competition.get('gender'),
                "match": sport_event.get('name'),
                "status": status.get('status'),
                "home_score": status.get('home_score'),
                "away_score": status.get('away_score'),
            })
        
        if not simplified_summaries:
            return f"No soccer summaries found for {date}."

        return json.dumps(simplified_summaries)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return "Error: Access denied. Please check your Sportradar API key and plan for the Daily Summaries endpoint."
        return f"Error fetching summaries from Sportradar: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def serpapi_search(query: str) -> str:
    """
    Searches the web using SerpApi's Google Search.

    Args:
        query: The search query.

    Returns:
        A string containing the search results.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not set.")

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
    }

    results = serpapi.search(params)
    return str(results.as_dict())

AVAILABLE_TOOLS = {
    "brave_search": brave_search,
    "get_soccer_summary_by_date": get_soccer_summary_by_date,
    "serpapi_search": serpapi_search,
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "brave_search",
            "description": "Use this tool to find real-time information from the internet, including news, facts, and answers to general knowledge questions. Input should be a clear and specific search query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A specific search query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_soccer_summary_by_date",
            "description": "Get a summary of soccer (football) matches for a specific date, including scores for completed games.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date to fetch the summary for, in YYYY-MM-DD format."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "serpapi_search",
            "description": "Leverages the SerpApi service to conduct real-time, comprehensive Google searches. This tool is ideal for accessing up-to-date information, answering questions about current events, or finding specific details on a wide range of topics by querying the Google search engine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# --- Pydantic Models & FastAPI App ---
# (The rest of the file is the same)
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False

app = FastAPI()
client = OpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [{"id": "gemini-2.5-flash", "object": "model", "created": int(time.time()), "owned_by": "google"}]}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # (The existing robust logic will handle the new tool)
    try:
        with open("system_prompt.txt", "r") as f:
            base_prompt = f.read().strip()
    except FileNotFoundError:
        return JSONResponse(status_code=500, content={"error": "system_prompt.txt not found."})

    today_date = datetime.now().strftime("%A, %B %d, %Y")
    system_prompt = f"{base_prompt}\n\nFor context, today's date is {today_date}."
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        messages.append(msg.model_dump(exclude_none=True))

    try:
        response = client.chat.completions.create(
            model=request.model, messages=messages, tools=tools_schema, tool_choice="auto"
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Error calling Gemini API: {e}"})

    response_message = response.choices[0].message
    messages.append(response_message.model_dump(exclude_none=True))

    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_to_call = AVAILABLE_TOOLS.get(function_name)
            if not function_to_call: continue

            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(**function_args) if function_args else function_to_call()
            
            messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response})
        
        final_response = client.chat.completions.create(
            model=request.model, messages=messages, stream=request.stream
        )
        
        if request.stream:
            def stream_generator(res):
                for chunk in res: yield f"data: {chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(stream_generator(final_response), media_type="text/event-stream")
        else:
            return final_response
    
    else:
        if request.stream:
            stream_response = client.chat.completions.create(
                model=request.model, messages=messages[:-1],
                tools=tools_schema, tool_choice="auto", stream=True
            )
            def stream_generator(res):
                for chunk in res: yield f"data: {chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(stream_generator(stream_response), media_type="text/event-stream")
        else:
            return response

if __name__ == "__main__":
    import uvicorn
    print("Starting OpenAI-compatible server on http://t.co/127.0.0.1:8005")
    uvicorn.run(app, host="127.0.0.1", port=8005)