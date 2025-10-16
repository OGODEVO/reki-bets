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
    st.caption("Built with Gemini & Streamlit")


# Main chat interface
st.title("Reki - AI Assistant")
st.caption("I can search the web and find today's soccer matches. Ask me anything!")

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
    try:
        with st.chat_message("assistant", avatar='💡'):
            with st.spinner("Reki is thinking..."):
                response = requests.post(API_URL, json=payload, stream=True)
                response.raise_for_status()
                
                full_response = ""
                placeholder = st.empty()
                
                for line in response.iter_lines():
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
                                except json.JSONDecodeError:
                                    st.error(f"Failed to decode JSON chunk: {content}")
                
                placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to the API server. Is it running? Error: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")