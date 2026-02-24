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

INSTRUCCIÓN DEL USUARIO PARA ESTA SESIÓN:
"{instruccion_inicial}"

REGLAS DE ENRUTAMIENTO ESTRICTAS:
1. Si la instrucción del usuario dice "MODO DIARIO":
   - El flujo debe ser estrictamente: Scout -> Analyst -> Translator.
   - Si el Traductor ya terminó su trabajo, responde 'FINISH'. (PROHIBIDO llamar al Publisher).

2. Si la instrucción del usuario dice "MODO SEMANAL":
   - Llama DIRECTAMENTE al Publisher. (NO llames al Scout, Analyst ni Translator).
   - Si el Publisher ya generó el PDF Y ADEMÁS ya envió el correo con éxito, responde 'FINISH'.

3. Si por algún motivo el último trabajador reporta un error crítico que impide continuar, responde 'FINISH'.

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
    
    raw_messages = state.get("messages", [])
    
    # Extraemos el primer mensaje (que es el prompt de tu run_daily o run_weekly)
    instruccion_inicial = "Ejecuta todo el flujo normal."
    if raw_messages:
        instruccion_inicial = raw_messages[0].content
    
    # 1. Preparamos las instrucciones inyectando el modo de ejecución
    system_prompt = SUPERVISOR_PROMPT.format(
        members=", ".join(MEMBERS),
        instruccion_inicial=instruccion_inicial
    )
    
    # 2. Construimos el historial textual
    history_text = "HISTORIAL DE ACCIONES:\n"
    if not raw_messages:
        history_text += "No hay acciones previas."
    else:
        for msg in raw_messages:
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