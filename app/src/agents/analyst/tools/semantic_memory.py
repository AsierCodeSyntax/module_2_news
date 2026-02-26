import os
import re
import psycopg
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "techwatch_items"
SIMILARITY_THRESHOLD = 0.85
CORRECTION_KEYWORDS = re.compile(r"\b(correction|update|debunk|false|falso|desmiente|retracted|errata|fixed|patch)\b", re.IGNORECASE)

model = SentenceTransformer("all-MiniLM-L6-v2")

def check_semantic_memory(item_id: int, topic: str, title: str, content: str, source_type: str = "") -> dict:
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    db_url = os.environ.get("DATABASE_URL")
    
    try:
        qdrant = QdrantClient(url=qdrant_url)
        text_to_embed = f"{topic}\n{title}\n{content}"
        vector = model.encode(text_to_embed).tolist()
        
        search_result = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            query_filter=Filter(must=[FieldCondition(key="topic", match=MatchValue(value=topic))]),
            limit=1,
            score_threshold=SIMILARITY_THRESHOLD
        ).points
        
        if search_result:
            match = search_result[0]
            original_id = match.payload.get("item_id")
            
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT source_type, COALESCE(llm_score, 0.0) FROM items WHERE id=%s", (original_id,))
                    orig_data = cur.fetchone()
                    
                    if not orig_data:
                        return {"action": "evaluate", "modifier": 0.0, "vector": vector}
                        
                    orig_source_type, orig_score = orig_data
                    
                    if CORRECTION_KEYWORDS.search(title):
                        cur.execute("UPDATE items SET llm_score = GREATEST(0.0, llm_score - 5.0) WHERE id=%s", (original_id,))
                        conn.commit()
                        return {"action": "evaluate", "modifier": -5.0, "vector": vector}
                        
                    elif source_type == 'official' and orig_source_type != 'official':
                        cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (original_id,))
                        conn.commit()
                        return {"action": "evaluate", "modifier": 1.0, "vector": vector}
                        
                    else:
                        cur.execute("UPDATE items SET llm_score = LEAST(llm_score + 1.0, 10.0), cluster_count = cluster_count + 1 WHERE id=%s", (original_id,))
                        conn.commit()
                        return {"action": "duplicate", "modifier": 0.0, "vector": vector}
        else:
            return {"action": "evaluate", "modifier": 0.0, "vector": vector}
            
    except Exception as e:
        print(f"❌ Error connecting to semantic memory: {e}")
        return {"action": "evaluate", "modifier": 0.0, "vector": None}