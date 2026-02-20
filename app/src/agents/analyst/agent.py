import os
import json
import psycopg
import uuid
import re
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from langchain_core.messages import AIMessage

from ..state import OverallState
from .skills.evaluate_article import evaluate_article_tool

COLLECTION_NAME = "techwatch_items"
SIMILARITY_THRESHOLD = 0.85
# Palabras clave de corrección/desmentido
CORRECTION_KEYWORDS = re.compile(r"\b(correction|update|debunk|false|falso|desmiente|retracted|errata|fixed|patch)\b", re.IGNORECASE)

def analyst_node(state: OverallState) -> dict:
    print("🧠 [Analyst] Ejecutando análisis REAL y CLUSTERING avanzado...")
    db_url = os.environ.get("DATABASE_URL")
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    
    model = SentenceTransformer("all-MiniLM-L6-v2")
    qdrant = QdrantClient(url=qdrant_url)
    
    procesados = 0; ecos = 0; correcciones = 0; duplicados = 0
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Añadimos source_type a la consulta para tu regla de autoridad
            cur.execute("SELECT id, topic, title, coalesce(content_text,''), source_type FROM items WHERE status='ready' AND qdrant_id IS NULL ORDER BY fetched_at DESC LIMIT 1")
            rows = cur.fetchall()
            
            for item_id, topic, title, content_text, source_type in rows:
                print(f"   Analizando noticia ID {item_id} ({topic})...")
                vector = model.encode(f"{topic}\n{title}\n{content_text}").tolist()
                
                # Búsqueda en Qdrant con filtro de Topic (tu código original)
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
                    
                    cur.execute("SELECT source_type, COALESCE(llm_score, 0.0), cluster_count FROM items WHERE id=%s", (original_id,))
                    orig_data = cur.fetchone()
                    
                    if not orig_data:
                        cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (item_id,))
                        duplicados += 1
                        continue
                        
                    orig_source_type, orig_score, orig_cluster = orig_data
                    
                    # CASO 1: Corrección / Desmentido
                    if CORRECTION_KEYWORDS.search(title):
                        print(f"   🚨 CORRECCIÓN/DESMENTIDO detectado: '{title[:30]}...'")
                        # Castigamos a la original
                        cur.execute("UPDATE items SET llm_score = GREATEST(0.0, llm_score - 5.0) WHERE id=%s", (original_id,))
                        
                        # Evaluamos la corrección y la guardamos
                        eval_json_str = evaluate_article_tool.invoke({"topic": topic, "title": title, "content": content_text})
                        try:
                            eval_data = json.loads(eval_json_str)
                            score = float(eval_data.get("score", 5.0))
                            summary = eval_data.get("summary_short", "Resumen no disponible.")
                        except:
                            score = 5.0; summary = "Error procesando corrección."
                        
                        new_qdrant_id = str(uuid.uuid4())
                        qdrant.upsert(collection_name=COLLECTION_NAME, points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})])
                        cur.execute("UPDATE items SET status='evaluated', summary_short=%s, llm_score=%s, qdrant_id=%s WHERE id=%s", (summary, score, new_qdrant_id, item_id))
                        correcciones += 1
                        
                    # CASO 2: Autoridad Oficial absorbe rumor
                    elif source_type == 'official' and orig_source_type != 'official':
                        print(f"   👑 AUTORIDAD OFICIAL: Absorbe rumor anterior.")
                        cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (original_id,))
                        
                        new_score = min(orig_score + 1.0, 10.0)
                        new_cluster = orig_cluster + 1
                        
                        eval_json_str = evaluate_article_tool.invoke({"topic": topic, "title": title, "content": content_text})
                        try:
                            eval_data = json.loads(eval_json_str)
                            summary = eval_data.get("summary_short", "Resumen no disponible.")
                        except:
                            summary = "Error procesando noticia oficial."
                            
                        new_qdrant_id = str(uuid.uuid4())
                        qdrant.upsert(collection_name=COLLECTION_NAME, points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})])
                        cur.execute("UPDATE items SET status='evaluated', summary_short=%s, llm_score=%s, cluster_count=%s, qdrant_id=%s WHERE id=%s", (summary, new_score, new_cluster, new_qdrant_id, item_id))
                        ecos += 1
                        
                    # CASO 3: Tendencia Normal (Eco)
                    else:
                        print(f"   📈 Tendencia (Eco): Suma puntos al original.")
                        cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (item_id,))
                        cur.execute("UPDATE items SET llm_score = LEAST(llm_score + 1.0, 10.0), cluster_count = cluster_count + 1 WHERE id=%s", (original_id,))
                        ecos += 1
                        duplicados += 1
                
                else:
                    # CASO 4: 100% Original
                    print("   ✅ Noticia nueva. Pidiendo evaluación al LLM...")
                    eval_json_str = evaluate_article_tool.invoke({"topic": topic, "title": title, "content": content_text})
                    
                    try:
                        eval_data = json.loads(eval_json_str)
                        score = float(eval_data.get("score", 5.0))
                        summary = eval_data.get("summary_short", "Resumen no disponible.")
                    except Exception as e:
                        score = 5.0; summary = "Error al procesar el texto."
                    
                    new_qdrant_id = str(uuid.uuid4())
                    qdrant.upsert(collection_name=COLLECTION_NAME, points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})])
                    
                    cur.execute("UPDATE items SET status='evaluated', summary_short=%s, llm_score=%s, qdrant_id=%s WHERE id=%s", (summary, score, new_qdrant_id, item_id))
                    procesados += 1
                    
        conn.commit()
    
    mensaje = f"Evaluadas {procesados} noticias nuevas, {ecos} ecos y {correcciones} desmentidos. Descartados {duplicados} duplicados. Pasa el turno al Translator."
    return {"messages": [AIMessage(content=mensaje)]}