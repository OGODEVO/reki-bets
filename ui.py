import streamlit as st
import requests
import json

# --- Configuration ---
API_URL = "http://127.0.0.1:8005/v1/chat/completions"
MODEL_NAME = "gemini-2.5-flash"

# --- Helper Functions ---
def new_chat():
    """Clears the chat history in the session state."""
    st.session_state.messages = []

# --- Streamlit UI ---
st.set_page_config(page_title="Reki - AI Assistant", layout="wide")

# Sidebar for chat management
with st.sidebar:
    st.title("🤖 Reki")
    st.write("Your AI Research Assistant.")
    st.button("➕ New Chat", on_click=new_chat, use_container_width=True)
    st.divider()
    st.caption("Reki 0.1")


# Main chat interface
st.title("Reki - AI Assistant")
st.caption("I can search the web and get the current NFL schedule. Ask me anything!")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past messages
for message in st.session_state.messages:
    avatar = '💬' if message["role"] == 'user' else '💡'
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("What can I help you with?"):
    # Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar='💬'):
        st.markdown(prompt)

    # Prepare request for the API
    api_messages = [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
    ]
    
    payload = {
        "model": MODEL_NAME,
        "messages": api_messages,
        "stream": True,
    }

    # --- Call the API and handle the stream ---
    full_response = ""
    try:
        with st.chat_message("assistant", avatar='💡'):
            spinner_message = "Reki is thinking..."
            
            # Peek at the first part of the stream to see if a tool is being called
            response = requests.post(API_URL, json=payload, stream=True)
            response.raise_for_status()
            
            # We need to handle the stream carefully
            lines = response.iter_lines()
            
            try:
                first_line = next(lines)
            except StopIteration:
                first_line = None

            tool_call_detected = False
            if first_line and first_line.decode('utf-8').startswith("data: "):
                content = first_line.decode('utf-8')[len("data: "):]
                if content != "[DONE]":
                    try:
                        chunk = json.loads(content)
                        if chunk.get("choices", [{}])[0].get("delta", {}).get("tool_calls"):
                            tool_name = chunk["choices"][0]["delta"]["tool_calls"][0]["function"]["name"]
                            if "nfl" in tool_name or "schedule" in tool_name or "nba" in tool_name:
                                spinner_message = "Calling NFL/NBA tool... 🏈🏀"
                            else:
                                spinner_message = f"Calling tool: `{tool_name}`..."
                            tool_call_detected = True
                    except (json.JSONDecodeError, IndexError):
                        pass # Not a valid tool call chunk

            with st.spinner(spinner_message):
                placeholder = st.empty()

                # Process the first line if we have it
                if first_line and not tool_call_detected:
                    if first_line:
                        decoded_line = first_line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            content = decoded_line[len("data: "):]
                            if content != "[DONE]":
                                try:
                                    chunk = json.loads(content)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                                    content_chunk = delta.get("content", "")
                                    if content_chunk:
                                        full_response += content_chunk
                                        placeholder.markdown(full_response + "▌")
                                except (json.JSONDecodeError, IndexError):
                                    pass # Ignore malformed chunks

                # Process the rest of the stream
                for line in lines:
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            content = decoded_line[len("data: "):]
                            if content != "[DONE]":
                                try:
                                    chunk = json.loads(content)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                                    content_chunk = delta.get("content", "")
                                    if content_chunk:
                                        full_response += content_chunk
                                        placeholder.markdown(full_response + "▌")
                                except (json.JSONDecodeError, IndexError):
                                    pass # Ignore malformed chunks
                
                placeholder.markdown(full_response)
        
            if full_response:
                st.session_state.messages.append({"role": "assistant", "content": full_response})

    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to the API server. Is it running? Error: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")