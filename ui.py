import streamlit as st
import requests
import json
import time
from typing import List, Dict, Any

# --- Configuration ---
API_URL = "http://127.0.0.1:8005/v1/chat/completions"
MODEL_NAME = "gemini-2.5-flash"
ASSISTANT_AVATAR = "🤖"
USER_AVATAR = "👤"

# --- Helper Functions ---
def initialize_session_state():
    """Initializes the session state with a welcome message."""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Welcome to Reki, your AI Sports Analyst. How can I assist you?"}]

def stream_api_response(api_payload: Dict[str, Any]):
    """
    Streams the response from the backend API, yielding content chunks and detecting tool calls.
    Returns a tuple: (generator, is_tool_call, tool_name)
    """
    is_tool_call = False
    tool_name = ""
    
    def response_generator():
        try:
            with requests.post(API_URL, json=api_payload, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            content = decoded_line[len("data: "):].strip()
                            if content and content != "[DONE]":
                                try:
                                    chunk = json.loads(content)
                                    yield chunk
                                except (json.JSONDecodeError, IndexError):
                                    continue
        except requests.exceptions.RequestException as e:
            error_chunk = {"error": {"message": f"Connection Error: {e}"}}
            yield error_chunk
        except Exception as e:
            error_chunk = {"error": {"message": f"An unexpected error occurred: {e}"}}
            yield error_chunk

    # Peek at the first chunk to detect a tool call
    stream = response_generator()
    try:
        first_chunk = next(stream)
        
        # Check for tool call in the first chunk
        tool_calls = first_chunk.get("choices", [{}])[0].get("delta", {}).get("tool_calls")
        if tool_calls:
            is_tool_call = True
            tool_name = tool_calls[0].get("function", {}).get("name", "Unknown Tool")

        # Yield the first chunk back to the main generator
        def combined_generator():
            yield first_chunk
            yield from stream
        
        return combined_generator(), is_tool_call, tool_name

    except StopIteration:
        return iter([]), False, ""


# --- Main UI Rendering ---
st.set_page_config(
    page_title="Reki - AI Sports Analyst",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
initialize_session_state()

# Sidebar
with st.sidebar:
    st.title(f"{ASSISTANT_AVATAR} Reki Analyst")
    st.markdown("---")
    st.markdown(
        "**Reki** is an enterprise-grade AI assistant designed for real-time sports data analysis and betting insights."
    )
    
    if st.button("Clear Chat History", use_container_width=True):
        initialize_session_state()
        st.rerun()

    st.markdown("---")
    st.markdown("### Resources")
    st.markdown("[View Documentation](https://example.com)")
    st.markdown("[API Status](https://example.com)")
    st.caption("© 2025 Reki AI")

# Main content area
st.title("Reki AI Sports Analyst")
st.caption(f"Powered by {MODEL_NAME}")

# Chat container
chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        avatar = ASSISTANT_AVATAR if message["role"] == "assistant" else USER_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

# User input
if prompt := st.chat_input("Ask for analysis on a game, team, or odds..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

    # Prepare and send API request
    api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    payload = {"model": MODEL_NAME, "messages": api_messages, "stream": True}
    
    response_stream, is_tool_call, tool_name = stream_api_response(payload)

    with chat_container:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            if is_tool_call:
                status = st.status(f"**Thinking...** (Using tool: `{tool_name}`)", expanded=True)
                # Consume the stream to let the backend finish, but don't display tool output directly
                for _ in response_stream:
                    pass
                status.update(label="**Analysis complete.**", state="complete", expanded=False)
                # This is a placeholder; the final text response is handled in the next turn
                # A more advanced implementation would update the UI after the tool call is fully processed
                # For now, we'll just show the "complete" status and wait for the user's next prompt
                # which will trigger the final response from the model.
                # This is a limitation of this simple Streamlit UI structure.
                # A better way would be to have the backend send a final text response after the tool call.
                # Since the backend is already doing that, we just need to process the stream.
                
                # Let's create a generator that extracts the final text from the stream
                def final_content_generator(stream):
                    final_text = ""
                    for chunk in stream:
                        if "error" in chunk:
                            final_text = f"An error occurred: {chunk['error']['message']}"
                            break
                        content_chunk = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content_chunk:
                            final_text += content_chunk
                    yield final_text

                # We need to re-run the stream to get the final response
                # This is not ideal, but it's how we can do it with the current backend
                final_stream, _, _ = stream_api_response(payload)
                final_response_text = "".join(final_content_generator(final_stream))
                st.markdown(final_response_text)
                st.session_state.messages.append({"role": "assistant", "content": final_response_text})


            else:
                # It's a direct text response
                def text_chunk_generator(stream):
                    for chunk in stream:
                        if "error" in chunk:
                            yield chunk["error"]["message"]
                            break
                        content_chunk = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content_chunk:
                            yield content_chunk
                
                full_response = st.write_stream(text_chunk_generator(response_stream))
                st.session_state.messages.append({"role": "assistant", "content": full_response})