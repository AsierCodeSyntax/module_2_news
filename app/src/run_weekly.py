from langchain_core.messages import HumanMessage
from agents.main_graph import main_graph

def main():
    print("🗞️ [Weekly] Iniciando generación del Boletín...")
    prompt = "MODO SEMANAL. Las noticias ya están en la base de datos. Ejecuta DIRECTAMENTE al Publisher para generar el PDF y enviar el correo. Cuando el Publisher termine, finaliza."
    
    initial_state = {"messages": [HumanMessage(content=prompt)], "next_agent": "", "errors": []}
    
    for event in main_graph.stream(initial_state, {"recursion_limit": 50}):
        pass
    print("✅ Boletín semanal generado.")

if __name__ == "__main__":
    main()