import os

def read_expert_skill(skill_name: str) -> str:
    """Reads the Markdown skill file to inject it into the expert's brain."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_path = os.path.join(base_dir, "skills", f"{skill_name}.md")
    
    if os.path.exists(skill_path):
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        print(f"❌ Error: The evaluation manual '{skill_name}.md' does not exist.")
        return ""