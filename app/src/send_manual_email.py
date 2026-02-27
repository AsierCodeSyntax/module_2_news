import sys
import json
import os
import psycopg
from agents.publisher.skills.send_gmail import send_gmail_tool

def main():
    print("🚀 [API] Iniciando envío de correo manual...")
    
    # 1. Enviar el correo
    result = send_gmail_tool.invoke({
        "subject": "TechWatch - Weekly News Bulletin",
        "body": "Kaixo!\n\nHemen duzu aste honetako berrien buletina (PDF formatuan erantsita).\n\nOndo izan,\nTechWatch Platform",
        "attachment_path": "/workspace/app/build/bulletin_compiled.pdf"
    })
    
    print(result)
    
    # Si la herramienta de gmail devuelve un error, salimos del script
    if "❌ Error" in result:
        sys.exit(1)

    # 2. "Consumir" las noticias (Marcarlas como publicadas)
    print("🗄️ [DB] Marcando las noticias enviadas como 'published'...")
    bulletin_path = "/workspace/app/build/bulletin.json"
    
    if os.path.exists(bulletin_path):
        with open(bulletin_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Extraer todos los IDs de las noticias que están en este boletín
        ids_to_publish = []
        for topic_key, topic_data in data.get("topics", {}).items():
            if "items" in topic_data:
                ids_to_publish.extend([item["id"] for item in topic_data["items"]])
            if "sections" in topic_data:
                for sec in topic_data["sections"]:
                    ids_to_publish.extend([item["id"] for item in sec.get("items", [])])
                    
        # Actualizar la base de datos
        if ids_to_publish:
            db_url = os.environ.get("DATABASE_URL")
            with psycopg.connect(db_url) as conn:
                with conn.cursor() as cur:
                    # Usamos ANY(%s) para actualizar múltiples IDs en una sola consulta
                    cur.execute(
                        "UPDATE items SET status = 'published' WHERE id = ANY(%s)",
                        (ids_to_publish,)
                    )
            print(f"✅ {len(ids_to_publish)} noticias actualizadas a 'published'.")
    else:
        print("⚠️ No se encontró bulletin.json. No se actualizó la BBDD.")

if __name__ == "__main__":
    main()