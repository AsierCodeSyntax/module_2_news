import os
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from ..state import OverallState

# Import tools from their proper location
from .tools.ingest_news import ingest_news_tool
from .tools.discovery import search_web_tool, verify_rss_tool, add_to_yaml_tool, blacklist_url_tool
from .tools.rss_manager import manage_rss_tool 
from .tools.skill_reader import read_expert_skill_tool
def get_scout_llm():
    print("🔌 [WARNING] Forcing direct connection with GEMINI 2.0 Flash...")
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = os.environ.get("GEMINI_API_KEY", "PUT_YOUR_KEY_HERE_IF_IT_FAILS")
    api_key = api_key.replace('"', '').replace("'", "")
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)

def load_master_guide() -> str:
    """Loads only the MASTER_GUIDE.md to act as the root index for the agent."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    master_guide_path = os.path.join(base_dir, "skills", "MASTER_GUIDE.md")
    
    if os.path.exists(master_guide_path):
        with open(master_guide_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return "⚠️ WARNING: MASTER_GUIDE.md not found in the skills/ directory."

def scout_node(state: OverallState) -> dict:
    print("🕵️‍♂️ [Scout] Starting OSINT discovery and ingestion mission...")
    
    master_guide_content = load_master_guide()
    llm = get_scout_llm()
    
    prompt = f"""
    You are the Senior OSINT & Feed Validation Specialist for an Advanced Tech Watch system.
    Your execution must be strict, fast, and of the highest quality.
    
    🧠 [YOUR MASTER OPERATING GUIDE]
    Read and strictly follow your standard operating procedure (SOP) below:
    
    {master_guide_content}
    
    ⚡ CRITICAL INSTRUCTIONS:
    1. Always follow the 'WORKFLOW' defined in your MASTER GUIDE.
    2. Read the sub-modules ('OSINT_SEARCH', 'SOURCE_VALIDATION') BEFORE taking action.
    3. If a feed is good, use 'add_to_yaml_tool'. If it is bad, use 'blacklist_url_tool'.
    4. OBLIGATORY FINAL STEP: You MUST execute 'ingest_news_tool'.
    """
    
    # 2. Update the tools array
    tools = [
        read_expert_skill_tool, 
        search_web_tool, 
        verify_rss_tool, 
        add_to_yaml_tool,       # <-- Back to YAML!
        blacklist_url_tool,     # <-- New blacklist tool!
        ingest_news_tool
    ]
    
    agent = create_react_agent(llm, tools)
    
    resultado = agent.invoke(
        {
            "messages": [
                SystemMessage(content=prompt),
                HumanMessage(content="Initiate your Scout mission.")
            ]
        },
        config={"recursion_limit": 25}
    )
    
    ultimo_mensaje = resultado["messages"][-1].content
    if not ultimo_mensaje or ultimo_mensaje.strip() == "":
        ultimo_mensaje = "Scout mission completed successfully."
        
    return {"messages": [AIMessage(content=ultimo_mensaje)]}