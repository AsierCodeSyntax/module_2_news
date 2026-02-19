import os
import requests
import google.generativeai as genai
from langgraph.graph import END

# Import the global state
from .state import OverallState

# Define the available workers (departments)
MEMBERS = ["Scout", "Analyst", "Translator", "Publisher"]

# System prompt forcing strict routing behavior
SUPERVISOR_PROMPT = """
You are a Supervisor managing the following workers: {members}.
Your job is to read the conversation and decide who should act next.

Routing options:
1. If you need to search for news or update RSS feeds -> call 'Scout'.
2. If there are raw news items that need technical evaluation -> call 'Analyst'.
3. If there are technical evaluations that need to be translated to Euskera -> call 'Translator'.
4. If everything is translated and it's time to generate the PDF or send emails -> call 'Publisher'.
5. If the main task is completely finished or there is nothing else to do -> respond 'FINISH'.

CRITICAL INSTRUCTION: Respond ONLY with the exact name of the worker or 'FINISH'. Do not add any extra text, punctuation, or explanation.
"""

def supervisor_node(state: OverallState) -> dict:
    """
    Supervisor node: reads the message history and decides the next step.
    Acts as the main router in the hierarchical graph.
    """
    print("👔 [Supervisor] Thinking about the next delegation...")
    
    messages = state.get("messages", [])
    system_prompt = SUPERVISOR_PROMPT.format(members=", ".join(MEMBERS))
    
    # Read the provider from the .env file
    provider = os.environ.get("SUPERVISOR_PROVIDER", "ollama").lower()
    
    # Build the conversation history for the prompt
    chat_history = f"Instructions: {system_prompt}\n\nHistory:\n"
    for msg in messages:
        chat_history += f"{msg.type}: {msg.content}\n"
    
    decision = "FINISH" # Default fallback
    
    try:
        if provider == "gemini":
            # Gemini implementation
            api_key = os.environ.get("GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            response = model.generate_content(chat_history)
            decision = response.text.strip().replace("'", "").replace('"', "")
            
        elif provider == "ollama":
            # Ollama implementation
            url = os.environ.get("OLLAMA_API_URL")
            model_name = os.environ.get("SUPERVISOR_MODEL", "gemma3:12b-cloud")
            api_key = os.environ.get("OLLAMA_API_KEY", "")
            
            if not url:
                raise ValueError("OLLAMA_API_URL is not set in .env")
                
            headers = {}
            if api_key and api_key != "Secreto":
                headers["Authorization"] = f"Bearer {api_key}"
                
            payload = {
                "model": model_name,
                "prompt": chat_history,
                "stream": False
            }
            
            # Handle API endpoint formatting
            base_url = url.rstrip('/')
            endpoint = f"{base_url}/generate" if base_url.endswith("/api") else f"{base_url}/api/generate"
            
            response = requests.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            # Clean up the response to ensure we only get the agent name
            raw_text = data.get("response", "").strip()
            decision = raw_text.replace("'", "").replace('"', "").split("\n")[0].strip()
            
        else:
            print(f"⚠️ [Supervisor] Unknown provider: {provider}")
            
    except Exception as e:
        print(f"❌ [Supervisor] Error during LLM call: {e}")
        # If the LLM fails, we finish the execution to avoid infinite loops
        decision = "FINISH"

    # Ensure the decision is exactly one of the allowed members or FINISH
    valid_decisions = MEMBERS + ["FINISH"]
    
    # Clean match (in case the LLM adds a period at the end)
    for valid in valid_decisions:
        if valid.lower() in decision.lower():
            decision = valid
            break
            
    if decision not in valid_decisions:
        print(f"⚠️ [Supervisor] Invalid output from LLM: '{decision}'. Forcing FINISH.")
        decision = "FINISH"

    print(f"👔 [Supervisor] Decision made -> {decision}")
    
    # LangGraph special signal to terminate the workflow
    if decision == "FINISH":
        return {"next_agent": END}
    
    return {"next_agent": decision}