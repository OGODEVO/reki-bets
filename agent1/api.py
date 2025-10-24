import os
import json
import time
import uuid
import requests
import serpapi
import pytz
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
TIMEZONE = os.getenv("TIMEZONE", "UTC")
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_BASE_URL = os.getenv("XAI_BASE_URL")

if not all([GEMINI_API_KEY, BRAVE_API_KEY, SPORTRADAR_API_KEY, SERPAPI_API_KEY]):
    raise ValueError("All API keys (GEMINI, BRAVE, SPORTRADAR, SERPAPI) must be set in .env file")

import subprocess
import sys

from nfl import get_nfl_current_week_schedule, get_nfl_game_statistics, get_nfl_game_roster, get_nfl_team_season_stats, find_nfl_game_by_teams_and_date
from nba import get_nba_daily_schedule, get_nba_daily_injuries, get_nba_game_summary, get_nba_seasonal_stats, get_nba_teams_list
from odds import get_daily_schedule_odds, get_sport_event_markets

# --- Tool Definitions & Schema ---

NBA_SCHEDULE_CACHE = {}
NBA_TEAMS_CACHE = {}

def clear_caches():
    """Clears all temporary data caches."""
    NBA_SCHEDULE_CACHE.clear()
    NBA_TEAMS_CACHE.clear()
    return {"status": "Caches cleared successfully."}

AVAILABLE_TOOLS = {
    "get_nfl_current_week_schedule": get_nfl_current_week_schedule,
    "find_nfl_game_by_teams_and_date": find_nfl_game_by_teams_and_date,
    "get_nfl_game_statistics": get_nfl_game_statistics,
    "get_nfl_game_roster": get_nfl_game_roster,
    "get_nfl_team_season_stats": get_nfl_team_season_stats,
    "get_nba_daily_schedule": get_nba_daily_schedule,
    "get_nba_daily_injuries": get_nba_daily_injuries,
    "get_nba_game_summary": get_nba_game_summary,
    "get_nba_seasonal_stats": get_nba_seasonal_stats,
    "get_nba_teams_list": get_nba_teams_list,
    # "get_daily_schedule_odds": get_daily_schedule_odds,
    # "get_sport_event_markets": get_sport_event_markets,
    "clear_caches": clear_caches,
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "find_nfl_game_by_teams_and_date",
            "description": "Finds a specific NFL game by the names of the two teams and the date of the game.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team1": {
                        "type": "string",
                        "description": "The name of the first NFL team (e.g., 'Seattle Seahawks')."
                    },
                    "team2": {
                        "type": "string",
                        "description": "The name of the second NFL team (e.g., 'Houston Texans')."
                    },
                    "date": {
                        "type": "string",
                        "description": "The date of the game in YYYY-MM-DD format."
                    }
                },
                "required": ["team1", "team2", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nfl_current_week_schedule",
            "description": "Fetches the NFL schedule for the current week, including game IDs, teams, venue, and broadcast info.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nfl_game_statistics",
            "description": "Fetches detailed statistics for a specific NFL game using its unique game ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "The unique identifier for the NFL game."
                    }
                },
                "required": ["game_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nfl_game_roster",
            "description": "Fetches the complete game roster for both teams in a specific NFL game.",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "The unique identifier for the NFL game."
                    }
                },
                "required": ["game_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nfl_team_season_stats",
            "description": "Fetches the seasonal statistics for a specific NFL team.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_identifier": {
                        "type": "string",
                        "description": "The name, abbreviation, or unique identifier for the NFL team."
                    },
                    "season_year": {
                        "type": "string",
                        "description": "The year of the season."
                    },
                    "season_type": {
                        "type": "string",
                        "description": "The type of season (e.g., REG, PRE, PST)."
                    }
                },
                "required": ["team_identifier", "season_year", "season_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nba_daily_schedule",
            "description": "Fetches the NBA daily schedule for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "The year of the schedule to fetch."
                    },
                    "month": {
                        "type": "integer",
                        "description": "The month of the schedule to fetch."
                    },
                    "day": {
                        "type": "integer",
                        "description": "The day of the schedule to fetch."
                    }
                },
                "required": ["year", "month", "day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nba_daily_injuries",
            "description": "Fetches the NBA daily injuries for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "The year of the injuries to fetch."
                    },
                    "month": {
                        "type": "integer",
                        "description": "The month of the injuries to fetch."
                    },
                    "day": {
                        "type": "integer",
                        "description": "The day of the injuries to fetch."
                    }
                },
                "required": ["year", "month", "day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nba_game_summary",
            "description": "Fetches a comprehensive game summary for a given NBA game, including live scores, team stats, and player rosters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "The unique identifier for the NBA game."
                    }
                },
                "required": ["game_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_caches",
            "description": "Clears all temporary data caches for NBA games and teams.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nba_seasonal_stats",
            "description": "Fetches complete team and player seasonal statistics for a given NBA team, season, and season type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "season_year": {
                        "type": "string",
                        "description": "The year of the season (e.g., '2023')."
                    },
                    "season_type": {
                        "type": "string",
                        "description": "The type of season. Can be 'REG' for regular season, 'PRE' for preseason, or 'PST' for postseason."
                    },
                    "team_id": {
                        "type": "string",
                        "description": "The unique identifier for the NBA team."
                    }
                },
                "required": ["season_year", "season_type", "team_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_nba_teams_list",
            "description": "Fetches a list of all NBA teams, including their names, aliases, and unique IDs.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }
]

# --- Pydantic Models & FastAPI App ---
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = True

app = FastAPI()

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "gemini-2.5-flash", "object": "model", "created": int(time.time()), "owned_by": "google"},
            {"id": "gemini-2.5-flash-lite", "object": "model", "created": int(time.time()), "owned_by": "google"},
            {"id": "grok-4-fast-reasoning", "object": "model", "created": int(time.time()), "owned_by": "xai"}
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    print(f"Received request for model: {request.model}")

    model_owner = next((item["owned_by"] for item in (await list_models())["data"] if item["id"] == request.model), None)

    if model_owner == "google":
        client = OpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    elif model_owner == "xai":
        client = OpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL)
    else:
        return JSONResponse(status_code=400, content={"error": f"Model '{request.model}' not found or owner not configured."})

    try:
        with open("system_prompt.txt", "r") as f:
            base_prompt = f.read().strip()
        with open("sports_state.json", "r") as f:
            sports_state = f.read()
    except FileNotFoundError as e:
        return JSONResponse(status_code=500, content={"error": f"{e.filename} not found."})

    try:
        user_tz = pytz.timezone(TIMEZONE)
    except pytz.UnknownTimeZoneError:
        return JSONResponse(status_code=400, content={"error": f"Invalid timezone specified: {TIMEZONE}"})

    today_date = datetime.now(user_tz).strftime("%A, %B %d, %Y %I:%M %p %Z")
    
    # Inject context into the prompt
    system_prompt = base_prompt.replace("{current_date}", today_date)
    system_prompt = system_prompt.replace("{sports_state}", sports_state)

    if NBA_SCHEDULE_CACHE:
        cached_games = [f"Game ID: {game['id']}, Teams: {game['away']['name']} vs {game['home']['name']}" for game in NBA_SCHEDULE_CACHE.get("games", [])]
        if cached_games:
            system_prompt += "\n\nFor your reference, here is the last NBA schedule you looked up. Use the game_id from this list for any follow-up questions:\n" + "\n".join(cached_games)
    
    # Limit the number of messages to the last 10 to avoid timeouts
    # Convert all messages to dictionaries for consistent processing
    messages_as_dicts = [msg.model_dump() if isinstance(msg, BaseModel) else msg for msg in request.messages]
    messages = [{"role": "system", "content": system_prompt}] + messages_as_dicts[-10:]

    async def stream_generator():
        yield "data: [STREAM_STARTED]\n\n"
        
        try:
            # First, get the initial response from the model. We'll consume the stream internally
            # to decide whether to yield it or to execute a tool first.
            initial_stream = client.chat.completions.create(
                model=request.model, 
                messages=messages, 
                tools=tools_schema, 
                tool_choice="auto", 
                stream=True
            )

            tool_calls = []
            initial_content_chunks = []
            
            for chunk in initial_stream:
                # Accumulate tool calls if they are present
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
                    tool_calls.extend(chunk.choices[0].delta.tool_calls)
                # Accumulate content chunks
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    initial_content_chunks.append(chunk)

            # --- Logic to handle response ---
            # If there are tool calls, execute them and stream the FINAL response.
            if tool_calls:
                # Reconstruct the full tool calls from the chunks
                full_tool_calls = []
                for tc in tool_calls:
                    if tc.id:
                        full_tool_calls.append({"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": ""}})
                    if tc.function and tc.function.arguments:
                        full_tool_calls[-1]["function"]["arguments"] += tc.function.arguments

                messages.append({"role": "assistant", "content": None, "tool_calls": full_tool_calls})

                # Execute the tools and append their results
                for tool_call in full_tool_calls:
                    function_name = tool_call["function"]["name"]
                    function_to_call = AVAILABLE_TOOLS.get(function_name)
                    if not function_to_call: continue
                    
                    try:
                        function_args = json.loads(tool_call["function"]["arguments"])
                        function_response = function_to_call(**function_args) if function_args else function_to_call()
                        
                        if function_name == "get_nba_daily_schedule":
                            NBA_SCHEDULE_CACHE.clear()
                            if isinstance(function_response, dict) and "games" in function_response:
                                NBA_SCHEDULE_CACHE["games"] = [
                                    {
                                        "id": game.get("id"),
                                        "away": {"name": game.get("away", {}).get("name")},
                                        "home": {"name": game.get("home", {}).get("name")}
                                    }
                                    for game in function_response["games"]
                                ]

                        if function_name == "get_nba_teams_list":
                            NBA_TEAMS_CACHE.clear()
                            if isinstance(function_response, dict) and "teams" in function_response:
                                NBA_TEAMS_CACHE["teams"] = [
                                    {
                                        "id": team.get("id"),
                                        "name": team.get("name"),
                                        "alias": team.get("alias")
                                    }
                                    for team in function_response["teams"]
                                ]
                    except Exception as e:
                        function_response = {"status": "error", "error": str(e)}

                    messages.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response),
                    })
                
                # Now, stream the definitive final response
                final_response_stream = client.chat.completions.create(
                    model=request.model, messages=messages, stream=True, tools=tools_schema, tool_choice="auto"
                )
                for chunk in final_response_stream:
                    yield f"data: {chunk.model_dump_json()}\n\n"

            # If there were NO tool calls, just stream the initial response we collected.
            else:
                for chunk in initial_content_chunks:
                    yield f"data: {chunk.model_dump_json()}\n\n"

        except Exception as e:
            print(f"Error during stream: {e}")
            error_message = {"error": str(e)}
            yield f"data: {json.dumps(error_message)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    if request.stream:
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        # Handle non-streaming case (though the user wants streaming)
        try:
            response = client.chat.completions.create(
                model=request.model, messages=messages, tools=tools_schema, tool_choice="auto"
            )
            return response
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Error calling Gemini API: {e}"})

if __name__ == "__main__":
    import uvicorn
    print("Starting OpenAI-compatible server on http://127.0.0.1:8005")
    uvicorn.run(app, host="127.0.0.1", port=8005)
