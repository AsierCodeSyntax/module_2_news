import os
import psycopg
from langchain_core.messages import AIMessage
from ..state import OverallState
from .skills.generate_pdf import generate_pdf_tool

def publisher_node(state: OverallState) -> dict:
    print("📰 [Publisher] Recopilando el TOP de noticias para el boletín LaTeX...")
    db_url = os.environ.get("DATABASE_URL")
    
    news_data = {
        "topics": {
            "plone": {"items": []},
            "django": {"items": []},
            "ai": {
                "sections": [
                    {"name": "Iturri Ofizialak", "items": []},
                    {"name": "ArXiv Ikerketak", "items": []}
                ]
            }
        }
    }
    all_ids = []
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Top 5 Plone
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='plone' AND status='translated' ORDER BY llm_score DESC LIMIT 100")
            for r in cur.fetchall():
                news_data["topics"]["plone"]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            # 2. Top 5 Django
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='django' AND status='translated' ORDER BY llm_score DESC LIMIT 5")
            for r in cur.fetchall():
                news_data["topics"]["django"]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            # 3. Top 5 AI (Oficiales/Otros) - Todo lo que NO contenga 'arxiv' en su source_id
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='ai' AND source_id NOT LIKE '%arxiv%' AND status='translated' ORDER BY llm_score DESC LIMIT 5")
            for r in cur.fetchall():
                news_data["topics"]["ai"]["sections"][0]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            # 4. Top 5 AI (ArXiv) - Todo lo que SÍ contenga 'arxiv' en su source_id
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='ai' AND source_id LIKE '%arxiv%' AND status='translated' ORDER BY llm_score DESC LIMIT 5")
            for r in cur.fetchall():
                news_data["topics"]["ai"]["sections"][1]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            if all_ids:
                cur.execute("UPDATE items SET status='published' WHERE id = ANY(%s)", (all_ids,))
        conn.commit()

    print(f"   📊 Recolectadas {len(all_ids)} noticias TOP. Compilando PDF...")
    resultado = generate_pdf_tool.invoke({"news_data": news_data})
    
    return {"messages": [AIMessage(content=f"Generación de PDF terminada: {resultado}")]}