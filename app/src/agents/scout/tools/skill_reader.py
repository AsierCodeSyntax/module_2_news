import os
from langchain_core.tools import tool

@tool
def read_expert_skill_tool(skill_name: str) -> str:
    """
    Skill: Lector de Conocimiento.
    Usa esta herramienta para leer tu manual de operaciones (SOP) ANTES de actuar.
    Ejemplo de skill_name: 'MASTER_GUIDE'
    """
    print(f"   📚 [Scout Skill: Reader] Consultando el manual: {skill_name}.md")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_path = os.path.join(base_dir, "skills", f"{skill_name}.md")
    
    if os.path.exists(skill_path):
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return f"❌ Error: El manual '{skill_name}.md' no existe."