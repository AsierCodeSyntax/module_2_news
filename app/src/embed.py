import os
import uuid
import re
from typing import List

import psycopg
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "techwatch_items"
SIMILARITY_THRESHOLD = 0.85

# Palabras clave que indican que una noticia es una corrección o desmentido
CORRECTION_KEYWORDS = re.compile(r"\b(correction|update|debunk|false|falso|desmiente|retracted|errata|fixed|patch)\b", re.IGNORECASE)

def process_batch(conn, qdrant, model, rows):
    duplicates_found = 0
    embedded_count = 0
    corrections_found = 0

    for item_id, topic, title, content_text, source_type in rows:
        text_to_embed = f"{title}\n{content_text}"
        vector = model.encode(text_to_embed).tolist()

        search_response = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            query_filter=Filter(must=[FieldCondition(key="topic", match=MatchValue(value=topic))]),
            limit=1,
            score_threshold=SIMILARITY_THRESHOLD
        )
        
        matches = search_response.points

        with conn.cursor() as cur:
            if matches:
                match = matches[0]
                original_id = match.payload.get("item_id")
                
                # ¿Es un desmentido/actualización?
                if CORRECTION_KEYWORDS.search(title):
                    print(f"[{topic}] 🚨 CORRECCIÓN/DESMENTIDO detectado: '{title[:40]}...'")
                    
                    # Penalizamos MUCHO a la noticia original (-5 puntos)
                    cur.execute(
                        "UPDATE items SET llm_score = llm_score - 5.0 WHERE id=%s",
                        (original_id,)
                    )
                    
                    # Y dejamos pasar esta nueva noticia como original para que el LLM la resuma
                    new_qdrant_id = str(uuid.uuid4())
                    qdrant.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})]
                    )
                    cur.execute("UPDATE items SET qdrant_id=%s WHERE id=%s", (new_qdrant_id, item_id))
                    embedded_count += 1
                    corrections_found += 1
                    
                else:
                    # Es un simple "eco" (Tendencia). 
                    print(f"[{topic}] 📈 Tendencia (Eco): '{title[:40]}...' suma puntos al original.")
                    
                    # Marcamos la nueva como duplicada
                    cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (item_id,))
                    
                    # Sumamos +1.0 al original, y aumentamos su cluster_count
                    cur.execute(
                        """
                        UPDATE items 
                        SET llm_score = LEAST(llm_score + 1.0, 10.0), 
                            cluster_count = cluster_count + 1 
                        WHERE id=%s
                        """,
                        (original_id,)
                    )
                    duplicates_found += 1
            else:
                # Es 100% original, lo subimos a Qdrant
                new_qdrant_id = str(uuid.uuid4())
                qdrant.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})]
                )
                cur.execute("UPDATE items SET qdrant_id=%s WHERE id=%s", (new_qdrant_id, item_id))
                embedded_count += 1

    conn.commit()
    return embedded_count, duplicates_found, corrections_found


def main():
    db_url = os.environ.get("DATABASE_URL")
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    
    if not db_url: raise SystemExit("DATABASE_URL not set")

    print("Cargando modelo de embeddings local...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    qdrant = QdrantClient(url=qdrant_url)

    if not qdrant.collection_exists(COLLECTION_NAME):
        qdrant.create_collection(collection_name=COLLECTION_NAME, vectors_config=VectorParams(size=384, distance=Distance.COSINE))

    total_embedded = 0
    total_duplicates = 0
    total_corrections = 0

    with psycopg.connect(db_url) as conn:
        # Bucle para procesar TODO hasta que no quede nada
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, topic, title, coalesce(content_text,'') as content_text, source_type
                    FROM items
                    WHERE status='ready' AND qdrant_id IS NULL
                    ORDER BY fetched_at ASC
                    LIMIT 200
                    """
                )
                rows = cur.fetchall()

            if not rows:
                break # Ya no quedan más!

            print(f"\nProcesando lote de {len(rows)} items...")
            emb, dup, corr = process_batch(conn, qdrant, model, rows)
            
            total_embedded += emb
            total_duplicates += dup
            total_corrections += corr

    print("\n=== RESUMEN QDRANT ===")
    print(f"Nuevos originales vectorizados: {total_embedded}")
    print(f"Ecos agrupados (+puntos al original): {total_duplicates}")
    print(f"Correcciones/Desmentidos (-puntos al original): {total_corrections}")

if __name__ == "__main__":
    main()