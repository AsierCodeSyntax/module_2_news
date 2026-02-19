import os
import psycopg
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

# Importamos nuestro flamante Grafo Agéntico
from agents.workflow import agent_app

COLLECTION_NAME = "techwatch_items"

def main():
    db_url = os.environ.get("DATABASE_URL")
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    
    if not db_url:
        raise SystemExit("DATABASE_URL no set.")

    # Inicializamos Qdrant y Modelo para guardar las noticias NUEVAS
    model = SentenceTransformer("all-MiniLM-L6-v2")
    qdrant = QdrantClient(url=qdrant_url)

    total_procesados = 0

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Seleccionamos las noticias que ya pasaron por enrich.py (status='ready')
            cur.execute(
                """
                SELECT id, topic, title, coalesce(content_text,'') as content_text
                FROM items
                WHERE status='ready' AND qdrant_id IS NULL
                ORDER BY fetched_at ASC
                LIMIT 50
                """
            )
            rows = cur.fetchall()

        if not rows:
            print("No hay noticias nuevas para procesar.")
            return

        for item_id, topic, title, content_text in rows:
            print(f"\n🚀 Inyectando al Grafo la noticia ID {item_id}: {title[:40]}...")

            # 1. Definimos el Estado Inicial para LangGraph
            initial_state = {
                "item_id": item_id,
                "topic": topic,
                "title": title,
                "content_text": content_text,
                "is_duplicate": False,
                "llm_score": 0.0,
                "summary_short": ""
            }

            # 2. INVOCAMOS AL AGENTE ORQUESTADOR
            # Aquí el Grafo decide si verifica, si termina, o si traduce.
            final_state = agent_app.invoke(initial_state)

            with conn.cursor() as cur:
                # 3. Reaccionamos a la decisión del Grafo
                if final_state["is_duplicate"]:
                    print("   📥 Actualizando BD: Marcado como duplicado.")
                    cur.execute("UPDATE items SET status='duplicate' WHERE id=%s", (item_id,))
                    # Nota: Aquí podrías añadir la lógica de 'Tendencias' (+1.0 punto) que tenías antes.
                
                else:
                    print("   📥 Actualizando BD: Noticia Evaluada y Traducida.")
                    # A. Guardamos el resumen y nota de la IA en Postgres
                    cur.execute(
                        """
                        UPDATE items 
                        SET status='evaluated', summary_short=%s, llm_score=%s 
                        WHERE id=%s
                        """,
                        (final_state["summary_short"], final_state["llm_score"], item_id)
                    )
                    
                    # B. Guardamos el vector en Qdrant para que la Skill de Memoria lo recuerde la próxima vez
                    new_qdrant_id = str(uuid.uuid4())
                    text_to_embed = f"{topic}\n{title}\n{content_text}"
                    vector = model.encode(text_to_embed).tolist()
                    
                    qdrant.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[PointStruct(id=new_qdrant_id, vector=vector, payload={"item_id": item_id, "topic": topic})]
                    )
                    
                    cur.execute("UPDATE items SET qdrant_id=%s WHERE id=%s", (new_qdrant_id, item_id))

            conn.commit()
            total_procesados += 1

    print(f"\n✅ Proceso completado. Noticias procesadas por el Grafo: {total_procesados}")

if __name__ == "__main__":
    main()