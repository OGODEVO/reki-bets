import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

# --- Environment Setup ---
# Load API keys from the .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env file.")
    exit()
if not BRAVE_API_KEY:
    print("ERROR: BRAVE_API_KEY not found in .env file.")
    exit()

# --- Tool Definition ---

def brave_search(query: str) -> str:
    """
    Performs a web search using the Brave Search API.

    Args:
        query: The search query.
    
    Returns:
        A JSON string of the search results.
    """
    print(f"Performing Brave search for: {query}")
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": query}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        results = response.json()
        # Let's return a simplified version for the model
        # We'll take the top 3 results and extract the title, url, and a snippet
        simplified_results = [
            {
                "title": item.get("title", "No Title"),
                "url": item.get("url", ""),
                "snippet": item.get("description", "No Snippet")
            }
            for item in results.get("web", {}).get("results", [])[:3]
        ]
        return json.dumps(simplified_results)
    except requests.exceptions.RequestException as e:
        return f"Error during search: {e}"
    except json.JSONDecodeError:
        return "Error: Could not decode search results from Brave API."


# --- Agent Setup ---

client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

AVAILABLE_TOOLS = {
    "brave_search": brave_search,
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "brave_search",
            "description": "Get information from the internet using Brave Search. Returns a list of search results with titles, URLs, and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# --- System Prompt ---
# Load the system prompt from the standalone text file.
try:
    with open("system_prompt.txt", "r") as f:
        SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    print("ERROR: system_prompt.txt not found. Please create it.")
    exit()
except Exception as e:
    print(f"ERROR: Could not read system_prompt.txt: {e}")
    exit()


# --- Main Agent Logic ---

def main():
    """The main function to run the agent."""
    
    print("Gemini Research Agent is ready. Ask me something! (Type 'quit' to exit)")
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        
        messages.append({"role": "user", "content": user_input})

        # Send the message to the model
        response = client.chat.completions.create(
            model="gemini-2.5-flash-lite",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True, # Enable streaming
        )

        tool_calls = []
        full_response_content = ""
        
        print("Agent: ", end="", flush=True)
        
        # Iterate over the streamed response chunks
        for chunk in response:
            delta = chunk.choices[0].delta
            
            if delta.content:
                print(delta.content, end="", flush=True)
                full_response_content += delta.content

            if delta.tool_calls:
                # Append the tool call chunks to our list
                if not tool_calls:
                    tool_calls.extend(delta.tool_calls)
                else:
                    for i, tool_call_chunk in enumerate(delta.tool_calls):
                        tool_calls[i].function.arguments += tool_call_chunk.function.arguments

        print() # Newline after streaming is complete

        # Check if the model wants to call a tool
        if tool_calls:
            # The model decided to use a tool
            assistant_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    } for tc in tool_calls
                ]
            }
            messages.append(assistant_message)
            
            # Call all the tools the model requested
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = AVAILABLE_TOOLS[function_name]
                function_args = json.loads(tool_call.function.arguments)
                
                function_response = function_to_call(**function_args)
                
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
            
            # Send the tool responses back to the model for a final summary
            final_response_stream = client.chat.completions.create(
                model="gemini-2.5-flash-lite",
                messages=messages,
                stream=True,
            )
            
            print("Agent: ", end="", flush=True)
            final_full_response = ""
            for chunk in final_response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
                    final_full_response += content
            print()
            
            messages.append({"role": "assistant", "content": final_full_response})

        else:
            # If no tool was called, just append the full response
            messages.append({"role": "assistant", "content": full_response_content})


if __name__ == "__main__":
    main()