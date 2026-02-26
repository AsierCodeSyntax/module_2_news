import os
import uuid
import psycopg
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

COLLECTION_NAME = "techwatch_items"

def get_pending_news(topic: str, limit: int = 100) -> list:
    """Fetches up to 'limit' pending news, filtering out items older than 14 days."""
    db_url = os.environ.get("DATABASE_URL")
    print(f"   📥 [Analyst: DB] Fetching pending news for '{topic.upper()}'...")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # 1. AUTO-CLEANUP: Mark old news as 'ignored_old' so they don't consume tokens
                # We use COALESCE just in case 'published_at' is NULL (it falls back to fetched_at)
                cur.execute(
                    """
                    UPDATE items 
                    SET status='ignored_old' 
                    WHERE status='ready' 
                      AND topic=%s 
                      AND COALESCE(published_at, fetched_at) < NOW() - INTERVAL '14 days'
                    """,
                    (topic,)
                )
                
                # Print how many old items were discarded to keep track
                discarded_count = cur.rowcount
                if discarded_count > 0:
                    print(f"      🧹 Auto-cleaned {discarded_count} old news (older than 14 days) for {topic.upper()}.")
                
                # 2. FETCH: Only fetch the remaining fresh news
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
                
                conn.commit()
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