import os
import sys
import json
import psycopg
from qdrant_client import QdrantClient
from qdrant_client.http import models

IDS_FILE = "/workspace/test_100_ids.json"
# 🚨 Cambia esto si tu colección en Qdrant se llama distinto (ej. "news")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "items") 

def get_db_url():
    return os.environ.get("DATABASE_URL", "postgresql://admin:admin@postgres:5432/techwatch")

def get_qdrant_client():
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    return QdrantClient(url=qdrant_url)

def borrar_memoria_qdrant(conn, selected_ids):
    """Busca los qdrant_id de las noticias seleccionadas y los borra de la BD Vectorial"""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT qdrant_id FROM items WHERE id = ANY(%s) AND qdrant_id IS NOT NULL", (selected_ids,))
            qdrant_ids = [str(row[0]) for row in cur.fetchall()]
                        
        if qdrant_ids:
            print(f"🧠 [Árbitro] Borrando {len(qdrant_ids)} recuerdos vectoriales en Qdrant...")
            client = get_qdrant_client()
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointIdsList(points=qdrant_ids)
            )
            print("✅ [Árbitro] Qdrant limpio. El Analista pensará que son noticias nuevas.")
    except Exception as e:
        print(f"⚠️ Aviso Qdrant: No se pudieron borrar los vectores (Quizás ya estaban borrados o el nombre de la colección no es '{COLLECTION_NAME}'). Error: {e}")

def prepare_test():
    print("🛠️ [Árbitro] Preparando el Test A/B y aplicando amnesia al sistema...")
    queries = {
        "AI (arXiv)": "SELECT id FROM items WHERE topic = 'ai' AND url ILIKE '%arxiv%' AND content_text IS NOT NULL ORDER BY published_at DESC NULLS LAST LIMIT 40",
        "AI (Oficial)": "SELECT id FROM items WHERE topic = 'ai' AND url NOT ILIKE '%arxiv%' AND content_text IS NOT NULL ORDER BY published_at DESC NULLS LAST LIMIT 30",
        "Django": "SELECT id FROM items WHERE topic = 'django' AND content_text IS NOT NULL ORDER BY published_at DESC NULLS LAST LIMIT 15",
        "Plone": "SELECT id FROM items WHERE topic = 'plone' AND content_text IS NOT NULL ORDER BY published_at DESC NULLS LAST LIMIT 15"
    }
    
    selected_ids = []
    try:
        with psycopg.connect(get_db_url()) as conn:
            with conn.cursor() as cur:
                for name, query in queries.items():
                    cur.execute(query)
                    ids = [row[0] for row in cur.fetchall()]
                    selected_ids.extend(ids)
                    
                with open(IDS_FILE, "w") as f:
                    json.dump(selected_ids, f)
                
                # 1. Borrar de Qdrant PRIMERO
                borrar_memoria_qdrant(conn, selected_ids)
                
                # 2. Ocultar todo el ruido
                cur.execute("UPDATE items SET status = 'oculto_ab_test' WHERE status IN ('new', 'ready')")
                
                # 3. Limpiar estado, prioridad y MUY IMPORTANTE: qdrant_id = NULL
                cur.execute("""
                    UPDATE items 
                    SET status = 'ready', 
                        priority = 0,
                        qdrant_id = NULL 
                    WHERE id = ANY(%s)
                """, (selected_ids,))
                
                conn.commit()
                print(f"✅ ¡Terreno de juego listo! {len(selected_ids)} noticias exactas listas para la Versión A.")
    except Exception as e:
        print(f"❌ Error DB: {e}")

def reset_test():
    print("🔄 [Árbitro] Reiniciando la prueba para la Ronda B...")
    if not os.path.exists(IDS_FILE):
        return
    with open(IDS_FILE, "r") as f:
        selected_ids = json.load(f)
    try:
        with psycopg.connect(get_db_url()) as conn:
            # 1. Borrar de Qdrant lo que la Versión A acaba de crear
            borrar_memoria_qdrant(conn, selected_ids)
            
            with conn.cursor() as cur:
                cur.execute("UPDATE items SET status = 'oculto_ab_test' WHERE status IN ('new', 'ready')")
                cur.execute("UPDATE items SET status = 'ready', priority = 0, qdrant_id = NULL WHERE id = ANY(%s)", (selected_ids,))
                conn.commit()
                print(f"✅ ¡Reinicio completo! Las mismas {len(selected_ids)} noticias listas para la Versión B.")
    except Exception as e:
        print(f"❌ Error DB: {e}")

if __name__ == "__main__":
    command = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if command == "prepare": prepare_test()
    elif command == "reset": reset_test()
    else: print("Usa 'prepare' o 'reset'")