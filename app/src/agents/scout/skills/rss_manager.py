import os
import requests
import feedparser
import psycopg
from langchain_core.tools import tool

@tool
def manage_rss_tool(action: str, url: str, topic: str = "", name: str = "") -> str:
    """
    Skill: Gestor de RSS.
    Permite validar, añadir o desactivar fuentes RSS en la base de datos PostgreSQL.
    - action: "check" (solo valida), "add" (valida y añade a la BD), "disable" (desactiva en la BD).
    - url: La URL del feed RSS.
    - topic: El tema (plone, django, ai). Obligatorio para la acción "add".
    - name: Nombre de la fuente (ej. "Blog de Django").
    """
    print(f"📡 [Scout Skill: RSS Manager] Acción: {action} | URL: {url}")
    
    # 1. Validar el RSS (Razonamiento previo a la acción)
    if action in ["check", "add"]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (TechWatchBot/1.0)',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            if not feed.entries:
                return f"❌ El RSS {url} responde, pero no contiene artículos válidos."
            
            if action == "check":
                return f"✅ RSS Válido. Contiene {len(feed.entries)} entradas. Ejemplo: {feed.entries[0].get('title')}"
                
        except Exception as e:
            return f"❌ Error validando el RSS {url}: {str(e)}"

    # 2. Actuar sobre la Base de Datos
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return "❌ Error interno: No se encuentra DATABASE_URL."

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                if action == "add":
                    if not topic:
                        return "❌ Error: Necesito saber el 'topic' (plone, django, ai) para guardar el RSS."
                    
                    source_id = name.lower().replace(" ", "_").replace(".", "")[:30] if name else "custom_rss"
                    cur.execute(
                        """
                        INSERT INTO sources (id, topic, source_type, name, url, enabled, updated_at)
                        VALUES (%s, %s, 'rss', %s, %s, true, now())
                        ON CONFLICT (id) DO UPDATE SET enabled = true, url = EXCLUDED.url
                        """,
                        (source_id, topic, name, url)
                    )
                    conn.commit()
                    return f"✅ RSS '{name}' guardado correctamente en la BD bajo el topic '{topic}'."
                    
                elif action == "disable":
                    cur.execute("UPDATE sources SET enabled = false WHERE url = %s", (url,))
                    conn.commit()
                    if cur.rowcount > 0:
                        return f"✅ Fuente RSS '{url}' desactivada en la BD."
                    return f"⚠️ No encontré ninguna fuente con esa URL para desactivar."
                    
    except Exception as e:
        return f"❌ Error de Base de Datos: {str(e)}"
        
    return "❌ Acción no válida. Usa 'check', 'add' o 'disable'."