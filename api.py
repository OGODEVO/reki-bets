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

import subprocess
import sys

from nfl import get_current_week_schedule, get_game_statistics, get_game_roster
from nba import get_daily_schedule, get_daily_injuries, get_game_summary
from odds import get_daily_schedule_odds

# --- Tool Definitions & Schema ---

AVAILABLE_TOOLS = {
    "get_current_week_schedule": get_current_week_schedule,
    "get_game_statistics": get_game_statistics,
    "get_game_roster": get_game_roster,
    "get_daily_schedule": get_daily_schedule,
    "get_daily_injuries": get_daily_injuries,
    "get_game_summary": get_game_summary,
    "get_daily_schedule_odds": get_daily_schedule_odds,
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_schedule_odds",
            "description": "Fetches the daily schedule odds for a given sport name and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sport_name": {
                        "type": "string",
                        "description": "The name of the sport (e.g., 'basketball', 'american_football')."
                    },
                    "date": {
                        "type": "string",
                        "description": "The date for which to fetch the schedule odds (format: YYYY-MM-DD)."
                    }
                },
                "required": ["sport_name", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_week_schedule",
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
            "name": "get_game_statistics",
            "description": "Fetches detailed statistics for a specific NFL game using its unique game ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "The unique identifier for the game."
                    }
                },
                "required": ["game_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_game_roster",
            "description": "Fetches the complete game roster for both teams in a specific NFL game.",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "The unique identifier for the game."
                    }
                },
                "required": ["game_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_schedule",
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
            "name": "get_daily_injuries",
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
            "name": "get_game_summary",
            "description": "Fetches the game summary for a given NBA game using its unique game ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "The unique identifier for the game."
                    }
                },
                "required": ["game_id"],
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
client = OpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "gemini-2.5-flash", "object": "model", "created": int(time.time()), "owned_by": "google"},
            {"id": "gemini-2.5-flash-lite", "object": "model", "created": int(time.time()), "owned_by": "google"}
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    print(f"Received request for model: {request.model}")

    try:
        with open("system_prompt.txt", "r") as f:
            base_prompt = f.read().strip()
    except FileNotFoundError:
        return JSONResponse(status_code=500, content={"error": "system_prompt.txt not found."})

    today_date = datetime.now().strftime("%A, %B %d, %Y")
    system_prompt = f"{base_prompt}\n\nFor context, today's date is {today_date}."
    
    # Limit the number of messages to the last 10 to avoid timeouts
    messages = [{"role": "system", "content": system_prompt}] + request.messages[-10:]

    async def stream_generator():
        yield "data: [STREAM_STARTED]\n\n"
        
        try:
            # First, stream the initial response from the model
            initial_stream = client.chat.completions.create(
                model=request.model, 
                messages=messages, 
                tools=tools_schema, 
                tool_choice="auto", 
                stream=True
            )

            tool_calls = []
            for chunk in initial_stream:
                yield f"data: {chunk.model_dump_json()}\n\n"
                # Check for tool calls in the stream
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
                    tool_calls.extend(chunk.choices[0].delta.tool_calls)

            # If there are tool calls, execute them and stream the final response
            if tool_calls:
                # Reconstruct the full tool calls from the chunks
                full_tool_calls = []
                for tc in tool_calls:
                    if tc.id:
                        full_tool_calls.append({"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": ""}})
                    if tc.function and tc.function.arguments:
                        full_tool_calls[-1]["function"]["arguments"] += tc.function.arguments

                # Append the assistant message with tool calls to the history
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": full_tool_calls
                })

                # Execute the tools
                for tool_call in full_tool_calls:
                    function_name = tool_call["function"]["name"]
                    function_to_call = AVAILABLE_TOOLS.get(function_name)
                    if not function_to_call: continue

                    function_args = json.loads(tool_call["function"]["arguments"])
                    function_response = function_to_call(**function_args) if function_args else function_to_call()
                    
                    messages.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    })
                
                # Stream the final response from the model
                final_response_stream = client.chat.completions.create(
                    model=request.model, messages=messages, stream=True
                )
                for chunk in final_response_stream:
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
