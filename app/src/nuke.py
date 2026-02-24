import os
import psycopg
from qdrant_client import QdrantClient

def nuke_everything():
    print("☢️ INICIANDO PROTOCOLO DE DESTRUCCIÓN TOTAL ☢️")
    
    # 1. Vaciar Postgres (solo la tabla items, para mantener la estructura)
    db_url = os.environ.get("DATABASE_URL", "postgresql://techwatch:techwatch@postgres:5432/techwatch")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # TRUNCATE vacía la tabla entera rapidísimo
                cur.execute("TRUNCATE items CASCADE;")
            conn.commit()
        print("✅ Postgres: Tabla 'items' aniquilada. Base de datos vacía.")
    except Exception as e:
        print(f"❌ Error en Postgres: {e}")

    # 2. Destruir colección en Qdrant
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    collection = "techwatch_items"
    try:
        client = QdrantClient(url=qdrant_url)
        if client.collection_exists(collection):
            client.delete_collection(collection_name=collection)
            print(f"✅ Qdrant: Colección '{collection}' destruida hasta los cimientos.")
        else:
            print(f"✅ Qdrant: La colección '{collection}' ya estaba vacía.")
    except Exception as e:
        print(f"❌ Error en Qdrant: {e}")

    print("✨ SISTEMA LIMPIO COMO UNA PATENA. Listo para empezar de 0 con noticias frescas.")

if __name__ == "__main__":
    nuke_everything()