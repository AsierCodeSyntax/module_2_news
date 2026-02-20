from langgraph.graph import StateGraph, START, END
from .state import OverallState
from .supervisor import supervisor_node

from .scout.agent import scout_node
from .analyst.agent import analyst_node
from .translator.agent import translator_node
from .publisher.agent import publisher_node # ⬅️ AHORA IMPORTAMOS EL NODO REAL

def create_main_graph():
    builder = StateGraph(OverallState)
    
    # 1. Nodos
    builder.add_node("Supervisor", supervisor_node)
    builder.add_node("Scout", scout_node)
    builder.add_node("Analyst", analyst_node)
    builder.add_node("Translator", translator_node)
    builder.add_node("Publisher", publisher_node) # ⬅️ SUSTITUIMOS EL DUMMY POR EL REAL
    
    # 2. Punto de entrada
    builder.add_edge(START, "Supervisor")
    
    # 3. Decisiones del Supervisor (Enrutamiento)
    builder.add_conditional_edges(
        "Supervisor",
        lambda state: state.get("next_agent", "FINISH"),
        {
            "Scout": "Scout",
            "Analyst": "Analyst",
            "Translator": "Translator",
            "Publisher": "Publisher",
            "FINISH": END,
            END: END
        }
    )
    
    # 4. Todos los agentes devuelven el control al Supervisor
    builder.add_edge("Scout", "Supervisor")
    builder.add_edge("Analyst", "Supervisor")
    builder.add_edge("Translator", "Supervisor")
    builder.add_edge("Publisher", "Supervisor")
    
    return builder.compile()

main_graph = create_main_graph()