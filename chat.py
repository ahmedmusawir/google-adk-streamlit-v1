# chat.py - FINAL, DEFINITIVE VERSION WITH SINGLE STATE OBJECT
import streamlit as st
import requests
import uuid
import json
from streamlit_local_storage import LocalStorage

# --- Page Configuration & API URLs ---
st.set_page_config(page_title="Cyberize Automation", page_icon="⚡")
st.title("⚡ Cyberize Agentic Automation")
N8N_WEBHOOK_URL = "http://127.0.0.1:5678/webhook/f11820f4-aaf0-4bb8-b536-b9097cc67877"
ADK_SERVER_URL = "http://127.0.0.1:8000"

# --- Initialize Local Storage ---
localS = LocalStorage()

# --- Single Point of State Initialization ---
# This block reads all persistent state from a single localStorage item.
def initialize_state():
    if 'state_initialized' in st.session_state:
        return

    profile_str = localS.getItem("user_profile")
    profile = json.loads(profile_str) if profile_str else {}
    
    st.session_state.user_id = profile.get("user_id") or f"st-user-{uuid.uuid4()}"
    st.session_state.agent_sessions = profile.get("agent_sessions", {})
    st.session_state.messages = []
    st.session_state.last_selected_agent = ""
    st.session_state.state_initialized = True

initialize_state()

# --- Helper Functions (No Changes) ---
def call_n8n_webhook(agent_name, message, user_id, session_id):
    """Sends a new message to an agent via the n8n orchestrator."""
    payload = {"agent_name": agent_name, "message": message, "userId": user_id, "session_id": session_id}
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=90)
        response.raise_for_status()
        outer_data = response.json()
        data_string = outer_data.get("data")
        if data_string: return json.loads(data_string)
        return {"message": "Error: 'data' key not found."}
    except Exception as e:
        st.error(f"Failed to connect to n8n: {e}")
        return {"message": f"Error: Could not reach orchestrator. Details: {e}"}

def fetch_history(agent_name, user_id, session_id):
    """Calls the ADK server directly to get the message history for a session."""
    if not session_id:
        return []
    try:
        url = f"{ADK_SERVER_URL}/apps/{agent_name}/users/{user_id}/sessions/{session_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        session_data = response.json()
        history = []
        if "events" in session_data:
            for event in session_data["events"]:
                if event.get("author") in ["USER", "MODEL"] and event.get("content"):
                    role = "user" if event["author"] == "USER" else "assistant"
                    content = event["content"].get("parts", [{}])[0].get("text", "")
                    if content:
                        history.append({"role": role, "content": content})
        return history
    except Exception as e:
        st.error(f"Failed to fetch history from ADK server: {e}")
        return []

# --- Sidebar ---
st.sidebar.title("Configuration")
agent_options = ["greeting_agent", "calc_agent", "jarvis_agent"]
selected_agent = st.sidebar.selectbox("Choose an agent:", options=agent_options)
st.sidebar.info(f"Chatting with: **{selected_agent}**")

# --- Main Chat Logic ---
if st.session_state.last_selected_agent != selected_agent:
    st.session_state.last_selected_agent = selected_agent
    resumed_session_id = st.session_state.agent_sessions.get(selected_agent)
    st.session_state.messages = fetch_history(selected_agent, st.session_state.user_id, resumed_session_id)
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(f"Ask {selected_agent} a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    current_session_id = st.session_state.agent_sessions.get(selected_agent)

    with st.spinner("Orchestrator is working..."):
        response_data = call_n8n_webhook(
            agent_name=selected_agent,
            message=prompt,
            user_id=st.session_state.user_id,
            session_id=current_session_id
        )

    assistant_response = response_data.get("message", "Error: No message content.")
    
    if "session_id" in response_data:
        st.session_state.agent_sessions[selected_agent] = response_data["session_id"]

    st.session_state.messages.append({"role": "assistant", "content": assistant_response})

    # --- Single Point of State Persistence ---
    # This block runs at the end of an interaction to save the updated state.
    profile_to_save = {
        "user_id": st.session_state.user_id,
        "agent_sessions": st.session_state.agent_sessions
    }
    localS.setItem("user_profile", json.dumps(profile_to_save))
    
    st.rerun()