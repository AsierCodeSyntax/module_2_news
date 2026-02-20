import os
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import END
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import OverallState

MEMBERS = ["Scout", "Analyst", "Translator", "Publisher"]

SUPERVISOR_PROMPT = """
Eres el Supervisor (Orquestador). Tu trabajo es leer el historial de la conversación y decidir a qué trabajador llamar a continuación.
Tus trabajadores son: {members}.

REGLAS DE ENRUTAMIENTO:
1. Si la petición requiere descargar o ingestar noticias y aún no se ha hecho -> responde 'Scout'.
2. Si el Scout ya terminó su ingesta y hay noticias pendientes de evaluar -> responde 'Analyst'.
3. Si el Analista ya evaluó y hay textos pendientes de traducir -> responde 'Translator'.
4. Si el Traductor ya terminó, REVISA LA PETICIÓN INICIAL. Si el usuario pidió generar un boletín o PDF, responde 'Publisher'. Si NO pidió generar PDF, responde 'FINISH'.
5. Si el Publisher ya generó el PDF con éxito -> responde 'FINISH'.

INSTRUCCIÓN CRÍTICA: Responde ÚNICAMENTE con una de estas palabras: Scout, Analyst, Translator, Publisher o FINISH. No añadas puntos, explicaciones, ni comillas.
"""

def get_supervisor_llm():
    """Instancia el LLM basándose en el archivo .env"""
    provider = os.environ.get("SUPERVISOR_PROVIDER", os.environ.get("LLM_PROVIDER", "ollama")).lower()
    
    if provider == "ollama":
        base_url = os.environ.get("OLLAMA_API_URL", "http://ollama:11434").replace("/api", "") + "/v1"
        return ChatOpenAI(
            base_url=base_url,
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            model=os.environ.get("SUPERVISOR_MODEL", os.environ.get("OLLAMA_MODEL", "gemma3:12b-cloud"))
        )
    else:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=os.environ.get("GEMINI_API_KEY")
        )

def supervisor_node(state: OverallState) -> dict:
    """Nodo del Supervisor de LangGraph"""
    print("👔 [Supervisor] Leyendo historial y decidiendo el siguiente paso...")
    
    # 1. Preparamos las instrucciones
    system_prompt = SUPERVISOR_PROMPT.format(members=", ".join(MEMBERS))
    
    # 2. BLINDAJE: Convertimos el historial complejo de LangChain en texto plano limpio.
    # Esto evita que Gemini se cuelgue por culpa de formatos extraños o "tool_calls" alucinados.
    raw_messages = state.get("messages", [])
    history_text = "HISTORIAL DE ACCIONES:\n"
    
    if not raw_messages:
        history_text += "No hay acciones previas."
    else:
        for msg in raw_messages:
            # Ponemos el tipo de mensaje y su contenido textual
            history_text += f"[{msg.type.upper()}]: {msg.content}\n"
            
    # 3. Creamos un único mensaje seguro para el LLM
    final_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=history_text)
    ]
    
    llm = get_supervisor_llm()
    
    try:
        response = llm.invoke(final_messages)
        # Limpiamos exhaustivamente la respuesta
        decision = response.content.strip().replace("'", "").replace('"', "").replace(".", "").split("\n")[0].strip()
    except Exception as e:
        print(f"❌ [Supervisor] Error llamando al LLM: {e}")
        decision = "FINISH"

    valid_decisions = MEMBERS + ["FINISH"]
    
    # Comprobación de seguridad para encajar la palabra exacta
    final_decision = "FINISH" # Por defecto
    for valid in valid_decisions:
        if valid.upper() in decision.upper():
            final_decision = valid
            break
            
    if final_decision == "FINISH":
        print("👔 [Supervisor] Decisión tomada -> Proceso terminado (FINISH).")
        return {"next_agent": END}
    
    print(f"👔 [Supervisor] Decisión tomada -> Delegando en: {final_decision}")
    return {"next_agent": final_decision}