import os
import yaml
import feedparser
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# Herramienta 1: Búsqueda web gratuita
search_web_tool = DuckDuckGoSearchRun()

@tool
def verify_rss_tool(url: str) -> str:
    """
    Skill: Verificador de RSS.
    Usa esto para comprobar si una URL descubierta en internet es realmente un feed RSS válido.
    """
    print(f"   🔍 Probando si '{url}' es un RSS válido...")
    try:
        feed = feedparser.parse(url)
        if feed.bozo == 0 and len(feed.entries) > 0:
            return f"✅ ÉXITO: RSS válido. Título del sitio: '{feed.feed.title}'. Contiene {len(feed.entries)} artículos recientes."
        else:
            return "❌ FALLO: La URL no es un RSS válido o está vacío."
    except Exception as e:
        return f"❌ FALLO TÉCNICO: No se pudo procesar el RSS. Error: {e}"

@tool
def add_to_yaml_tool(topic: str, source_name: str, url: str) -> str:
    """
    Skill: Editor de Configuración.
    Usa esto ÚNICAMENTE después de haber verificado que un RSS funciona.
    Añade la nueva fuente al archivo sources.yaml.
    """
    yaml_path = "/workspace/app/src/sources.yaml"
    print(f"   ✍️ [Scout] Escribiendo nueva fuente en sources.yaml: {source_name} ({topic})")
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            sources = yaml.safe_load(f) or {}
            
        if topic not in sources:
            sources[topic] = {}
        if 'rss' not in sources[topic]:
            sources[topic]['rss'] = []
            
        # Comprobar si ya existe
        for feed in sources[topic]['rss']:
            if feed.get('url') == url:
                return "⚠️ La fuente ya existía en el archivo."
                
        # Añadir la nueva
        sources[topic]['rss'].append({'name': source_name, 'url': url})
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(sources, f, allow_unicode=True, default_flow_style=False)
            
        return f"✅ Fuente '{source_name}' añadida permanentemente a {topic}."
    except Exception as e:
        return f"❌ Error al escribir el YAML: {e}"