import os
import psycopg

def get_news_to_translate(limit: int = 200) -> list:
    """Fetches news that have been evaluated but not yet translated."""
    db_url = os.environ.get("DATABASE_URL")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, summary_short 
                    FROM items 
                    WHERE status='evaluated' 
                    ORDER BY fetched_at DESC 
                    LIMIT %s
                    """,
                    (limit,)
                )
                return cur.fetchall()
    except Exception as e:
        print(f"❌ DB Error fetching news to translate: {e}")
        return []

def save_translation(item_id: int, title_eu: str, summary_eu: str) -> bool:
    """Saves the Basque translation and updates the status to 'translated'."""
    db_url = os.environ.get("DATABASE_URL")
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
                return True
    except Exception as e:
        print(f"❌ Error saving translation in DB: {e}")
        return False