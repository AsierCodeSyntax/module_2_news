import os
import json
import re
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

def get_eval_llm():
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
def evaluate_article_tool(topic: str, title: str, content: str) -> str:
    """
    Skill: Evalúa el nivel técnico de un artículo.
    Devuelve un JSON con el 'score' (0 a 10) y un 'summary_short'.
    """
    print(f"🤖 [Analyst Skill: LLM] Evaluando nivel técnico de: '{title[:40]}...'")
    llm = get_eval_llm()
    
    prompt = f"""
    Eres un analista técnico experto en {topic}. Evalúa la relevancia, impacto y novedad de este artículo.
    Asigna una puntuación del 0.0 al 10.0. Un artículo irrelevante o genérico merece una nota mas baja que un anuncio crítico o vulnerabilidad grave.

    REGLA CRÍTICA PARA EL RESUMEN: Ve directo al grano. NO uses frases introductorias como "Este artículo trata de...". Escribe directamente el hecho principal (ej: "Se ha descubierto una vulnerabilidad crítica en...").
    
    Título: {title}
    Contenido: {content[:1500]}
    
    IMPORTANTE: Devuelve ÚNICAMENTE un objeto JSON válido. El 'score' DEBE ser tu propia evaluación matemática, NO COPIES EL EJEMPLO:
    {{
        "score": 7.3,
        "summary_short": "Resumen muy breve y directo de 2 líneas."
    }}
    """
    
    messages = [
        SystemMessage(content="You are a strict JSON-only evaluation engine."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        content_res = response.content.strip()
        
        # --- EL LIMPIADOR DE JSON ---
        content_res = content_res.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', content_res, re.DOTALL)
        
        if match:
            clean_json_str = match.group(0)
            json.loads(clean_json_str) # Comprobamos que no explota
            return clean_json_str
        else:
            raise ValueError("No se encontró estructura JSON")
            
    except Exception as e:
        print(f"❌ [Analyst Skill] Error de formato: {e}")
        # Si todo falla, devolvemos un JSON válido para que Python no pete
        return json.dumps({
            "score": 5.0,
            "summary_short": f"No se pudo evaluar automáticamente el artículo."
        })