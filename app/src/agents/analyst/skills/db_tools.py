import os
import uuid
import psycopg
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
from langchain_core.tools import tool

# Inicializamos dependencias globales para esta skill
COLLECTION_NAME = "techwatch_items"
model = SentenceTransformer("all-MiniLM-L6-v2")

@tool
def get_pending_news_tool(limit: int = 5) -> str:
    """
    Skill: Obtener Noticias Pendientes.
    Busca en PostgreSQL noticias con status='ready' y sin qdrant_id que necesitan ser analizadas.
    Devuelve un string con el formato JSON de los artículos.
    """
    db_url = os.environ.get("DATABASE_URL")
    print("📥 [Analyst Skill: DB] Buscando noticias pendientes...")
    
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, topic, title, coalesce(content_text,'') as content_text
                    FROM items
                    WHERE status='ready' AND qdrant_id IS NULL
                    ORDER BY fetched_at ASC
                    LIMIT %s
                    """,
                    (limit,)
                )
                rows = cur.fetchall()
        
        if not rows:
            return "No hay noticias nuevas para analizar."
            
        result = []
        for r in rows:
            result.append(f"ID: {r[0]} | Topic: {r[1]} | Title: {r[2]} | Content: {r[3][:300]}...")
        return "\n".join(result)
    except Exception as e:
        return f"❌ Error leyendo BD: {str(e)}"


@tool
def save_analysis_tool(item_id: int, status: str, topic: str = "", title: str = "", content: str = "", summary: str = "", score: float = 0.0) -> str:
    """
    Skill: Guardar Análisis.
    Usa esta herramienta para guardar el resultado de tu análisis.
    - item_id: El ID numérico de la noticia.
    - status: 'duplicate' (si es repetida) o 'evaluated' (si es nueva y valiosa).
    - topic, title, content: Necesarios SOLO si el status es 'evaluated' (para generar el vector Qdrant).
    - summary: El resumen corto (solo si es 'evaluated').
    - score: La nota técnica del 0 al 10 (solo si es 'evaluated').
    """
    db_url = os.environ.get("DATABASE_URL")
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    print(f"💾 [Analyst Skill: DB] Guardando item {item_id} como '{status}'")
    
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                if status == 'duplicate':
                    cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (item_id,))
                    conn.commit()
                    return f"✅ Item {item_id} marcado como duplicado."
                
                elif status == 'evaluated':
                    # 1. Guardar resumen y score en Postgres
                    cur.execute(
                        """
                        UPDATE items 
                        SET status='evaluated', summary_short=%s, llm_score=%s 
                        WHERE id=%s
                        """,
                        (summary, score, item_id)
                    )
                    
                    # 2. Generar Vector y guardarlo en Qdrant para la memoria futura
                    qdrant = QdrantClient(url=qdrant_url)
                    new_qdrant_id = str(uuid.uuid4())
                    text_to_embed = f"{topic}\n{title}\n{content}"
                    vector = model.encode(text_to_embed).tolist()
                    
                    qdrant.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})]
                    )
                    
                    # 3. Vincular Qdrant ID en Postgres
                    cur.execute("UPDATE items SET qdrant_id=%s WHERE id=%s", (new_qdrant_id, item_id))
                    conn.commit()
                    return f"✅ Item {item_id} evaluado (Score: {score}) y memorizado en Qdrant."
                else:
                    return "❌ Status no válido. Usa 'duplicate' o 'evaluated'."
    except Exception as e:
        return f"❌ Error guardando en BD/Qdrant: {str(e)}"