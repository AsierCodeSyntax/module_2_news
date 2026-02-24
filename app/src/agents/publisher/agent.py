import os
import re
import psycopg
from langchain_core.messages import AIMessage
from ..state import OverallState
from .skills.generate_pdf import generate_pdf_tool
from .skills.send_gmail import send_gmail_tool # <-- AÑADIMOS EL IMPORT

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
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='plone' AND status='translated' AND llm_score >= 6 ORDER BY llm_score DESC LIMIT 5")
            for r in cur.fetchall():
                news_data["topics"]["plone"]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            # 2. Top 5 Django
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='django' AND status='translated' AND llm_score >= 6 ORDER BY llm_score DESC LIMIT 5")
            for r in cur.fetchall():
                news_data["topics"]["django"]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            # 3. Top 5 AI (Oficiales/Otros) - Todo lo que NO contenga 'arxiv' en su source_id
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='ai' AND source_id NOT LIKE '%arxiv%' AND status='translated' AND llm_score >= 6 ORDER BY llm_score DESC LIMIT 5")
            for r in cur.fetchall():
                news_data["topics"]["ai"]["sections"][0]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            # 4. Top 5 AI (ArXiv) - Todo lo que SÍ contenga 'arxiv' en su source_id
            cur.execute("SELECT id, title, summary_short, url, llm_score FROM items WHERE topic='ai' AND source_id LIKE '%arxiv%' AND status='translated' AND llm_score >= 6 ORDER BY llm_score DESC LIMIT 5")
            for r in cur.fetchall():
                news_data["topics"]["ai"]["sections"][1]["items"].append({"id": r[0], "title": r[1], "summary_short": r[2], "url": r[3], "llm_score": r[4]})
                all_ids.append(r[0])
                
            if all_ids:
                cur.execute("UPDATE items SET status='published' WHERE id = ANY(%s)", (all_ids,))
        conn.commit()

    print(f"   📊 Recolectadas {len(all_ids)} noticias TOP. Compilando PDF...")
    
    # --- PASO 1: GENERAR PDF ---
    resultado_pdf = generate_pdf_tool.invoke({"news_data": news_data})
    
    # Verificamos si hubo error
    if "❌" in resultado_pdf:
        return {"messages": [AIMessage(content=f"Error en Publisher. Falló la generación del PDF: {resultado_pdf}")]}
        
    # --- PASO 2: EXTRAER LA RUTA DEL PDF ---
    # Buscamos la ruta absoluta que devuelve tu tool (ej: /workspace/app/build/archive/...)
    ruta_match = re.search(r'(/workspace/[^\s]+\.pdf)', resultado_pdf)
    
    if not ruta_match:
         return {"messages": [AIMessage(content=f"Error en Publisher. Se generó el PDF pero no se encontró la ruta en el mensaje: {resultado_pdf}")]}
         
    ruta_absoluta = ruta_match.group(1)
    
    # --- PASO 3: ENVIAR EL CORREO ---
    print("   📧 Preparando el envío del correo electrónico...")
    resultado_correo = send_gmail_tool.invoke({
        "subject": "Boletín Semanal de Vigilancia Tecnológica",
        "body": "Hola,\n\nAdjunto tienes el informe en PDF con las noticias más relevantes sobre Plone, Django y AI.\n\nUn saludo.",
        "attachment_path": ruta_absoluta
    })
    
    # Devolvemos el mensaje final al Supervisor para que sepa que TODO terminó y diga 'FINISH'
    mensaje_final = f"Proceso del Publisher completado. PDF Generado ({ruta_absoluta}) y {resultado_correo}"
    return {"messages": [AIMessage(content=mensaje_final)]}