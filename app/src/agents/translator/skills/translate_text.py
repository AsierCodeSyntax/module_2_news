import os
import json
import re
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

def get_translation_llm():
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        base_url = os.environ.get("OLLAMA_API_URL", "http://ollama:11434").replace("/api", "") + "/v1"
        return ChatOpenAI(
            base_url=base_url,
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            model=os.environ.get("OLLAMA_MODEL", "gemma3:12b-cloud")
        )
    else:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.environ.get("GEMINI_API_KEY")
        )

@tool
def translate_to_euskera_tool(title: str, summary: str) -> str:
    """
    Skill: Traducción a Euskera.
    Traduce el título y el resumen de un artículo técnico al Euskera.
    """
    print("🗣️ [Translator Skill: LLM] Traduciendo textos al Euskera...")
    llm = get_translation_llm()
    
    prompt = f"""
    Eres un traductor profesional técnico experto en euskera (Batua). 
    Traduce el siguiente título y resumen del inglés o castellano al euskera con estilo DIRECTO y PERIODÍSTICO.
    
    REGLA DE ESTILO CRÍTICA:
    ELIMINA cualquier muletilla introductoria como "Este artículo trata sobre...", "El texto menciona que...", "La noticia informa que...", etc.
    Ve directamente al hecho. En lugar de decir "Artikulu honek Plone 3.1 kaleratu dela dio", debes decir directamente "Plone 3.1 bertsioa kaleratu da...".
    Mantén los términos técnicos (como 'AI', 'Plone', 'Django', 'Framework') en su formato original si no tienen una traducción clara.
    
    Título original: {title}
    Resumen original: {summary}

    IMPORTANTE: Devuelve ÚNICAMENTE un objeto JSON válido con este formato exacto, sin explicaciones ni Markdown extra:
    {{
        "title_eu": "título traducido aquí",
        "summary_eu": "resumen directo y al grano traducido aquí"
    }}
    """
    
    messages = [
        SystemMessage(content="You are a JSON-only translation engine."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # --- EL LIMPIADOR DE JSON ---
        # 1. Quitamos los bloques de markdown si el LLM es desobediente
        content = content.replace("```json", "").replace("```", "").strip()
        
        # 2. Buscamos la primera llave { y la última } por si metió texto antes o después
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            clean_json_str = match.group(0)
            # Verificamos que es válido parseándolo
            json.loads(clean_json_str) 
            return clean_json_str
        else:
            raise ValueError("No se encontró estructura JSON en la respuesta")
            
    except Exception as e:
        print(f"❌ [Translator Skill] Error de traducción o formato: {e}")
        # Devolvemos un JSON seguro ("fallback") para que el script no pete
        fallback_json = json.dumps({
            "title_eu": f"(Itzulpen errorea) {title}",
            "summary_eu": f"(Itzulpen errorea) {summary}"
        })
        return fallback_json