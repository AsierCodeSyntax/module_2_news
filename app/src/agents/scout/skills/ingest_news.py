import subprocess
from langchain_core.tools import tool

@tool
def ingest_news_tool(topic: str) -> str:
    """
    Skill: Ingesta de Noticias.
    Ejecuta el proceso automático de descarga y enriquecimiento de noticias 
    para un tema específico (plone, django, ai).
    """
    print(f"📥 [Scout Skill: Ingest] Descargando y enriqueciendo noticias de: {topic}")
    workspace_dir = "/workspace"
    
    try:
        # 1. Descarga RSS
        subprocess.run(["python", "app/src/ingest.py", "--topic", topic], check=True, cwd=workspace_dir, capture_output=True, text=True)
        # 2. Descarga Scrape
        subprocess.run(["python", "app/src/ingest_scrape.py", "--topic", topic], check=True, cwd=workspace_dir, capture_output=True, text=True)
        # 3. ENRIQUECIMIENTO (El eslabón perdido: Pasa de 'new' a 'ready')
        subprocess.run(["python", "app/src/enrich.py"], check=True, cwd=workspace_dir, capture_output=True, text=True)
        
        return f"✅ Noticias del topic '{topic}' descargadas, enriquecidas y listas (ready) para el Analista."
    except subprocess.CalledProcessError as e:
        return f"❌ Fallo en la ingesta de '{topic}'. Revisa los logs: {e.stderr}"