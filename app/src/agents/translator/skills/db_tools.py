import os
import psycopg
from langchain_core.tools import tool

@tool
def get_news_to_translate_tool(limit: int = 5) -> str:
    """
    Skill: Obtener Noticias para Traducir.
    Busca en PostgreSQL noticias con status='evaluated' (ya puntuadas por el Analista pero aún en español/inglés).
    Devuelve un string con los IDs, títulos y resúmenes a traducir.
    """
    db_url = os.environ.get("DATABASE_URL")
    print("📥 [Translator Skill: DB] Buscando noticias pendientes de traducción...")
    
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, summary_short 
                    FROM items 
                    WHERE status='evaluated' 
                    ORDER BY fetched_at ASC 
                    LIMIT %s
                    """,
                    (limit,)
                )
                rows = cur.fetchall()
        
        if not rows:
            return "No hay noticias pendientes de traducción."
            
        result = []
        for r in rows:
            result.append(f"ID: {r[0]}\nTítulo Original: {r[1]}\nResumen Original: {r[2]}\n---")
        return "\n".join(result)
    except Exception as e:
        return f"❌ Error leyendo BD: {str(e)}"


@tool
def save_translation_tool(item_id: int, title_eu: str, summary_eu: str) -> str:
    """
    Skill: Guardar Traducción.
    Guarda en la base de datos el título y el resumen traducidos al Euskera.
    Cambia el estado de la noticia a 'translated'.
    """
    db_url = os.environ.get("DATABASE_URL")
    print(f"💾 [Translator Skill: DB] Guardando traducción para el item {item_id}...")
    
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE items 
                    SET title=%s, summary_short=%s, status='translated' 
                    WHERE id=%s
                    """,
                    (title_eu, summary_eu, item_id)
                )
                conn.commit()
                return f"✅ Item {item_id} actualizado con textos en Euskera y marcado como 'translated'."
    except Exception as e:
        return f"❌ Error guardando traducción en BD: {str(e)}"