import os
import json
import psycopg
from langchain_core.messages import AIMessage

from ..state import OverallState
from .skills.translate_text import translate_to_euskera_tool

def translator_node(state: OverallState) -> dict:
    print("🌍 [Translator] Ejecutando traducción REAL en Python...")
    db_url = os.environ.get("DATABASE_URL")
    traducidos = 0
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, summary_short FROM items WHERE status='evaluated' ORDER BY fetched_at DESC LIMIT 1")
            rows = cur.fetchall()
            
            for item_id, title, summary in rows:
                print(f"   Traduciendo noticia ID {item_id}...")
                trans_json_str = translate_to_euskera_tool.invoke({"title": title, "summary": summary})
                try:
                    trans_data = json.loads(trans_json_str)
                    title_eu = trans_data.get("title_eu", title)
                    summary_eu = trans_data.get("summary_eu", summary)
                except:
                    title_eu = title; summary_eu = summary
                
                cur.execute("UPDATE items SET title=%s, summary_short=%s, status='translated' WHERE id=%s", (title_eu, summary_eu, item_id))
                traducidos += 1
        conn.commit()
    
    mensaje = f"Traducción terminada. He traducido {traducidos} noticias."
    return {"messages": [AIMessage(content=mensaje)]}