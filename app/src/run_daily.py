from langchain_core.messages import HumanMessage
from agents.main_graph import main_graph

def main():
    print("🌅 [Daily] Iniciando rutina diaria...")
    prompt = "Ejecuta el ciclo diario: 1. Scout 2. Analyst 3. Translator. NO ejecutes el Publisher."
    initial_state = {"messages": [HumanMessage(content=prompt)], "next_agent": "", "errors": []}
    
    for event in main_graph.stream(initial_state, {"recursion_limit": 50}):
        pass # Ejecuta en silencio o con prints, como prefieras
    print("✅ Rutina diaria completada.")

if __name__ == "__main__":
    main()