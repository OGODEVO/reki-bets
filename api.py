import os
import json
import time
import uuid
import requests
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
SPORTMONKS_API_KEY = os.getenv("SPORTMONKS_API_KEY")

if not all([GEMINI_API_KEY, BRAVE_API_KEY, SPORTMONKS_API_KEY]):
    raise ValueError("All API keys (GEMINI, BRAVE, SPORTMONKS) must be set in .env file")

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

def get_todays_soccer_matches() -> str:
    """Gets a list of today's soccer matches from the Sportmonks API."""
    print("Getting today's soccer matches...")
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.sportmonks.com/v3/football/fixtures/date/{today}"
    params = {"api_token": SPORTMONKS_API_KEY, "include": "participants"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        fixtures = response.json().get("data", [])
        
        simplified_fixtures = [
            {
                "home_team": next((p['name'] for p in fix['participants'] if p['meta']['location'] == 'home'), 'N/A'),
                "away_team": next((p['name'] for p in fix['participants'] if p['meta']['location'] == 'away'), 'N/A'),
                "league": fix.get('league', {}).get('name', 'N/A'),
                "starting_time": fix.get('starting_at', 'N/A')
            }
            for fix in fixtures[:10]
        ]
        return json.dumps(simplified_fixtures)
    except Exception as e:
        return f"Error fetching soccer matches: {e}"

AVAILABLE_TOOLS = {
    "brave_search": brave_search,
    "get_todays_soccer_matches": get_todays_soccer_matches,
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
                        "description": "A specific and clear search query to find information on the internet. For example: 'latest news on AI advancements' or 'who won the 2022 world cup'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_todays_soccer_matches",
            "description": "Fetches a list of scheduled soccer (football) matches for the current date. Use this tool when a user asks about today's games, schedules, or who is playing. It provides the home team, away team, league, and the match's starting time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# --- OpenAI-compatible Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False

# --- FastAPI App ---
app = FastAPI()
client = OpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [{"id": "gemini-2.5-flash", "object": "model", "created": int(time.time()), "owned_by": "google"}]}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Dynamically add today's date to the system prompt for each request
    today_date = datetime.now().strftime("%A, %B %d, %Y")
    dynamic_prompt = f"{SYSTEM_PROMPT}\n\nFor context, today's date is {today_date}."

    # Prepend the dynamic system prompt to the user's messages
    user_messages = [msg.model_dump(exclude_none=True) for msg in request.messages]
    messages = [{"role": "system", "content": dynamic_prompt}] + user_messages
    
    response = client.chat.completions.create(
        model=request.model, messages=messages, tools=tools_schema, tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    messages.append(response_message)
    
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_to_call = AVAILABLE_TOOLS[function_name]
            if function_name == "get_todays_soccer_matches":
                function_response = function_to_call()
            else:
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(**function_args)

            messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response})
        
        final_response = client.chat.completions.create(model=request.model, messages=messages, stream=request.stream)
        
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
                model=request.model, messages=[msg.model_dump(exclude_none=True) for msg in request.messages],
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
    print("Starting OpenAI-compatible server on http://127.0.0.1:8005")
    uvicorn.run(app, host="127.0.0.1", port=8005)