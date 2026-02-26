import os
import uuid
import psycopg
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

COLLECTION_NAME = "techwatch_items"

def get_pending_news(topic: str, limit: int = 100) -> list:
    """Fetches up to 'limit' pending news for a specific topic."""
    db_url = os.environ.get("DATABASE_URL")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, coalesce(content_text,'') as content_text, source_type
                    FROM items
                    WHERE status='ready' AND qdrant_id IS NULL AND topic=%s
                    ORDER BY fetched_at ASC
                    LIMIT %s
                    """,
                    (topic, limit)
                )
                return cur.fetchall()
    except Exception as e:
        print(f"❌ DB Error fetching news: {e}")
        return []

def save_analysis(item_id: int, topic: str, status: str, summary: str = "", final_score: float = 0.0, vector: list = None) -> bool:
    """Saves the final evaluation and the Qdrant vector."""
    db_url = os.environ.get("DATABASE_URL")
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                if status == 'duplicate':
                    cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (item_id,))
                    conn.commit()
                    return True
                
                elif status == 'evaluated':
                    cur.execute(
                        """
                        UPDATE items 
                        SET status='evaluated', summary_short=%s, llm_score=%s 
                        WHERE id=%s
                        """,
                        (summary, final_score, item_id)
                    )
                    
                    if vector:
                        qdrant = QdrantClient(url=qdrant_url)
                        new_qdrant_id = str(uuid.uuid4())
                        qdrant.upsert(
                            collection_name=COLLECTION_NAME,
                            points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})]
                        )
                        cur.execute("UPDATE items SET qdrant_id=%s WHERE id=%s", (new_qdrant_id, item_id))
                        
                    conn.commit()
                    return True
    except Exception as e:
        print(f"❌ Error saving to DB/Qdrant: {e}")
        return False