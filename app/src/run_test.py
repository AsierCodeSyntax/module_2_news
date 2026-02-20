import os
from langchain_core.messages import HumanMessage
from agents.main_graph import main_graph

def main():
    print("🚀 Iniciando prueba del Grafo Multi-Agente (Scout -> Analyst -> Translator)")
    
    # Le damos la instrucción inicial al Supervisor
    prompt = """
    Hola equipo. Por favor, realizad el ciclo completo diario:
    1. Ejecutad la ingesta de noticias.
    2. Analizad las noticias pendientes (descartando duplicados y puntuando las nuevas).
    3. Traducid los análisis al euskera.
    4. Genera el PDF final.
    """
    
    initial_state = {
        "messages": [HumanMessage(content=prompt.strip())],
        "next_agent": "",
        "errors": []
    }
    
    # Usamos .stream() en lugar de .invoke() para ver paso a paso qué hace cada agente en la consola
    config = {"recursion_limit": 50} # Límite de saltos para evitar bucles infinitos
    
    try:
        for event in main_graph.stream(initial_state, config):
            for node_name, node_state in event.items():
                print(f"\n--- 🔄 FIN DEL TURNO DE: {node_name} ---")
                if "messages" in node_state and node_state["messages"]:
                    print(f"Último mensaje: {node_state['messages'][-1].content}")
    except Exception as e:
        print(f"\n❌ Se detuvo la ejecución por un error: {e}")

    print("\n✅ Prueba del Grafo finalizada.")

if __name__ == "__main__":
    main()