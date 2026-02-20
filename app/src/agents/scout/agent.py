import os
from langchain_core.messages import AIMessage
from ..state import OverallState
from .skills.ingest_news import ingest_news_tool

def scout_node(state: OverallState) -> dict:
    print("🕵️‍♂️ [Scout] Ejecutando ingesta de noticias para TODOS los topics...")
    
    # 1. Ejecutamos la ingesta para todos tus temas
    topics = ["plone", "django", "ai"]
    resultados = []
    
    for t in topics:
        print(f"   📥 Descargando: {t}...")
        res = ingest_news_tool.invoke({"topic": t})
        resultados.append(f"[{t.upper()}]: {res}")
    
    # 2. Informamos al Supervisor
    mensaje_para_supervisor = (
        "He completado la ingesta para todos los topics. Resultados:\n" +
        "\n".join(resultados) +
        "\nMi trabajo ha terminado. Pasa el turno al Analyst."
    )
    
    return {"messages": [AIMessage(content=mensaje_para_supervisor)]}