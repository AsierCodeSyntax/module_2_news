import os
import yaml
import feedparser
from ddgs import DDGS
import requests
from langchain_core.tools import tool
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from langchain_core.tools import tool

BLACKLIST_FILE = "/workspace/app/src/blacklist.txt"
# Variable global para contar los fallos durante esta ejecución
intentos_fallidos = 0 

def get_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def add_to_blacklist(url):
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        f.write(f"{url}\n")

@tool
def search_web_tool(query: str) -> str:
    """Skill: Web Search. Finds tech blogs and extracts hidden RSS/Atom feeds."""
    print(f"   🌐 [Scout Skill] Searching web for: '{query}'...")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
        if not results:
            return "No se encontraron webs."
            
        blacklist = get_blacklist()
        feeds_encontrados = []
        
        # 🚨 LA LISTA DE EXCLUSIÓN: Foros y redes sociales donde no hay RSS de blogs
        basura_social = ['reddit.com', 'youtube.com', 'twitter.com', 'facebook.com', 
                         'instagram.com', 'stackoverflow.com', 'github.com', 'zhihu.com', 
                         'linkedin.com', 'ycombinator.com', 'pinterest.com']
        
        for r in results:
            url_web = r.get('href', '')
            
            # Si está en la blacklist o es una red social, lo ignoramos de inmediato
            if any(bad in url_web for bad in blacklist) or any(basura in url_web for basura in basura_social):
                continue
                
            print(f"   🕵️‍♂️ Inspeccionando el HTML de: {url_web[:60]}...")
            
            try:
                # Simulamos ser un navegador real y moderno
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                resp = requests.get(url_web, headers=headers, timeout=5)
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Buscamos el RSS oculto
                for link in soup.find_all('link', rel='alternate'):
                    if link.get('type') in ['application/rss+xml', 'application/atom+xml']:
                        rss_link = link.get('href')
                        if rss_link:
                            url_rss_final = urljoin(url_web, rss_link)
                            feeds_encontrados.append(f"- URL RSS ENCONTRADA: {url_rss_final}\n  Blog original: {r.get('title')}\n")
                            print(f"   ✅ ¡RSS Oculto encontrado!: {url_rss_final}")
                            break # Dejamos de buscar en este HTML
                            
                if len(feeds_encontrados) >= 2:
                    break
                    
            except Exception as inner_e:
                # Imprimimos por si la web nos bloquea la conexión (ej. Error 403)
                print(f"      [!] Fallo al escanear {url_web[:30]}: {inner_e}")
                pass 
                
        if not feeds_encontrados:
            return "Busqué en varios blogs pero ninguno tenía la etiqueta de RSS activada en su HTML. Intenta buscar otra temática."
            
        return "\n".join(feeds_encontrados)
        
    except Exception as e:
        # 🚨 Si DuckDuckGo nos bloquea, ahora lo veremos en la consola
        print(f"   ❌ [Error Crítico DDG]: {e}")
        return f"❌ Error en la búsqueda web: DuckDuckGo bloqueó la petición ({e})."



@tool
def verify_rss_tool(url: str) -> str:
    """
    Skill: RSS Validator & Content Sampler.
    Checks if a URL is a valid RSS/Atom feed and returns a sample of its latest articles 
    so you (the LLM) can semantically evaluate its quality and relevance.
    """
    global intentos_fallidos
    print(f"   🔍 [Scout Skill] Validating and sampling content from: '{url}'...")
    
    try:
        feed = feedparser.parse(url)
        # Check if it's a valid feed with at least one article
        if getattr(feed, 'bozo', 0) == 0 and len(feed.entries) > 0:
            
            # Prepare a sample for the LLM to read
            sample_text = f"✅ SUCCESS. Valid feed found. Site Title: '{feed.feed.title}'.\n\n--- CONTENT SAMPLE FOR EVALUATION ---\n"
            
            # Extract the latest 3 entries to give the LLM context
            for i, entry in enumerate(feed.entries[:3]):
                title = entry.get('title', 'No title')
                # Extract summary and strip HTML tags to save tokens and keep it readable
                raw_summary = entry.get('summary', '')
                clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text(separator=" ", strip=True)
                # Truncate to 300 chars to avoid overwhelming the context window
                clean_summary = clean_summary[:300] + "..." if len(clean_summary) > 300 else clean_summary
                
                sample_text += f"📰 Article {i+1}: {title}\n📝 Summary: {clean_summary}\n\n"
            
            sample_text += "👉 YOUR TASK: Analyze this sample using your SOURCE_VALIDATION criteria. Is it high quality? If YES, use 'add_to_yaml_tool'. If NO (e.g. it is generic, low tier, or irrelevant), you MUST use 'blacklist_url_tool' on this URL to prevent future visits."
            
            return sample_text
        else:
            intentos_fallidos += 1
            add_to_blacklist(url)
            return f"❌ FAILED: Invalid or empty RSS. URL added to BLACKLIST. (Fails: {intentos_fallidos}/5)."
            
    except Exception as e:
        intentos_fallidos += 1
        add_to_blacklist(url)
        return f"❌ TECHNICAL ERROR: Could not parse RSS. Added to BLACKLIST. (Fails: {intentos_fallidos}/5)."

@tool
def add_to_yaml_tool(topic: str, source_name: str, url: str, score: int) -> str:
    """
    Skill: Configuration Editor.
    Adds the verified source to sources_ia.yaml. Valid topics: 'ai', 'plone', 'django'.
    You MUST provide a 'score' (from 1 to 10) based on how authoritative and technical the source is.
    Maintains a limit per topic. When full, it removes the lowest-scored source first.
    """
    yaml_path = "/workspace/sources_ia.yaml"
    MAX_SOURCES_PER_TOPIC = 5
    
    print(f"   ✍️ [Scout Skill] Writing to YAML. Source: '{source_name}', Score: {score}/10")
    try:
        # Create file if it doesn't exist
        if not os.path.exists(yaml_path):
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump({}, f)
                
        with open(yaml_path, 'r', encoding='utf-8') as f:
            sources = yaml.safe_load(f) or {}
            
        if topic not in sources:
            sources[topic] = {}
        if 'rss' not in sources[topic]:
            sources[topic]['rss'] = []
            
        # Prevent duplicates
        for feed in sources[topic]['rss']:
            if feed.get('url') == url:
                return "⚠️ Source already existed in YAML. Proceed to the next step."
                
        # 🧹 SMART CLEANUP (Evict lowest score first)
        if len(sources[topic]['rss']) >= MAX_SOURCES_PER_TOPIC:
            # Sort the list by score ascending.
            # If scores are equal, Python's stable sort keeps the older ones first.
            sources[topic]['rss'].sort(key=lambda x: x.get('score', 5)) 
            
            # Pop the first item (which is now the lowest score / oldest among lowest)
            removed_source = sources[topic]['rss'].pop(0)
            print(f"   🧹 [Scout Skill] Limit reached. Evicted lowest quality source: '{removed_source.get('url')}' (Score: {removed_source.get('score', 'N/A')})")
            
        # Append the new verified source with its score
        sources[topic]['rss'].append({'name': source_name, 'url': url, 'score': score})
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(sources, f, allow_unicode=True, default_flow_style=False)
            
        return f"✅ Source '{source_name}' (Score: {score}) successfully added to '{topic}'. Proceed to the next step."
    except Exception as e:
        return f"❌ Critical error writing to YAML: {e}. Abort this action and proceed to ingestion."
    
@tool
def blacklist_url_tool(url: str) -> str:
    """
    Skill: Blacklist Manager.
    Use this tool to permanently ban a URL that you have evaluated as irrelevant, low quality, or not technical enough.
    """
    print(f"   🚫 [Scout Skill: Blacklist] Adding URL to blacklist: {url}")
    add_to_blacklist(url)
    return f"✅ URL '{url}' added to blacklist. We will not visit it again."