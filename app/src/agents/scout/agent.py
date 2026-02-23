import os
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from ..state import OverallState
from .skills.ingest_news import ingest_news_tool
from .skills.discovery import search_web_tool, verify_rss_tool, add_to_yaml_tool

def get_scout_llm():
    print("🔌 [ATENCIÓN] Forzando conexión directa con GEMINI 2.0 Flash...")
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = os.environ.get("GEMINI_API_KEY", "PON_TU_CLAVE_AQUI_SI_FALLA")
    api_key = api_key.replace('"', '').replace("'", "")
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)

def scout_node(state: OverallState) -> dict:
    print("🕵️‍♂️ [Scout] Iniciando misión de descubrimiento e ingesta...")
    llm = get_scout_llm()
    
    prompt = """
    Eres el Agente Scout de un sistema de vigilancia tecnológica. Tienes DOS misiones exactas.
    
    MISIÓN 1: BÚSQUEDA Y EVALUACIÓN CRÍTICA (MÁXIMO 5 FALLOS)
    1. Usa 'search_web_tool' para encontrar webs que contengan feeds RSS sobre 'ai', 'plone' o 'django'.
    2. Usa 'verify_rss_tool' en la URL del RSS encontrado.
    3. IMPORTANTE: 'verify_rss_tool' te devolverá una muestra de los últimos artículos de ese feed.
        - DEBES LEER ESA MUESTRA. Eres un experto técnico. Si los artículos hablan de temas genéricos, 
          historia, foros irrelevantes o no son altamente técnicos sobre tu topic, RECHÁZALO.
        - Solo si el contenido es de alta calidad técnica y relevante para el topic, guárdalo con 'add_to_yaml_tool'.
    4. Si llevas 5 fallos acumulados, ABORTA INMEDIATAMENTE la Misión 1.
    
    MISIÓN 2: INGESTA DIARIA (OBLIGATORIA)
    - Cuando termines la Misión 1, EJECUTA 'ingest_news_tool' (topics: 'plone', 'django', 'ai').
    
    Al terminar la Misión 2, responde detallando si añadiste algún feed nuevo y confirma que la ingesta ha terminado.
    """
    
    tools = [search_web_tool, verify_rss_tool, add_to_yaml_tool, ingest_news_tool]
    
    # Creamos el agente SIN el parámetro problemático
    agent = create_react_agent(llm, tools)
    
    # Ejecutamos el agente inyectando las instrucciones como SystemMessage
    # y le damos margen de 20 iteraciones para probar URLs
    resultado = agent.invoke(
        {
            "messages": [
                SystemMessage(content=prompt),
                HumanMessage(content="Inicia tu misión Scout.")
            ]
        },
        config={"recursion_limit": 20}
    )
    
    ultimo_mensaje = resultado["messages"][-1].content
    if not ultimo_mensaje or ultimo_mensaje.strip() == "":
        ultimo_mensaje = "Misiones del Scout completadas por defecto."
        
    return {"messages": [AIMessage(content=ultimo_mensaje)]}