import os
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

# 1. Strict schema definition for the LLM output
class TranslationResult(BaseModel):
    title_eu: str = Field(description="The translated title in Basque (Euskera)")
    summary_eu: str = Field(description="The translated summary in Basque (Euskera) using a direct, journalistic style")

def get_translator_llm():
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        from langchain_openai import ChatOpenAI
        base_url = os.environ.get("OLLAMA_API_URL", "http://ollama:11434").replace("/api", "") + "/v1"
        llm = ChatOpenAI(
            base_url=base_url,
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            model=os.environ.get("OLLAMA_MODEL", "gemma3:12b-cloud"),
            max_retries=2,       
            timeout=45.0
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.environ.get("GEMINI_API_KEY", "PUT_YOUR_KEY_HERE_IF_IT_FAILS")
        api_key = api_key.replace('"', '').replace("'", "")
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, max_retries=2, timeout=45.0)
        
    # We force the structured output
    return llm.with_structured_output(TranslationResult)

def translate_content(llm_with_structure, title: str, summary: str) -> TranslationResult:
    """Invokes the LLM to translate the content and returns a Pydantic object."""
    print("      🗣️  [Translator: LLM] Translating text to Euskera...")
    
    system_prompt = SystemMessage(content="""
    You are a professional technical translator expert in Basque (Euskera Batua). 
    Translate the following title and summary from English or Spanish to Basque using a DIRECT and JOURNALISTIC style.
    
    CRITICAL STYLE RULE:
    REMOVE any introductory filler phrases like "This article is about...", "The text mentions that...", "The news reports that...", etc.
    Get straight to the point. Instead of saying "Artikulu honek Plone 3.1 kaleratu dela dio", you must say directly "Plone 3.1 bertsioa kaleratu da...".
    Keep technical terms (like 'AI', 'Plone', 'Django', 'Framework') in their original format if they don't have a clear translation.
    """)
    
    user_msg = HumanMessage(content=f"Original Title: {title}\nOriginal Summary: {summary}")
    
    return llm_with_structure.invoke([system_prompt, user_msg])