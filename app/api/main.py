import os
import json
import subprocess
import requests
import psycopg
import trafilatura 
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="TechWatch API", description="API para el Dashboard de React")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="/workspace/app/build"), name="static")

class ManualNewsInput(BaseModel):
    url: str
    topic: str

@app.get("/")
def read_root():
    return {"status": "TechWatch API is running and ready! 🚀"}

@app.get("/api/bulletin/latest")
def get_latest_bulletin():
    bulletin_path = "/workspace/app/build/bulletin.json"
    if not os.path.exists(bulletin_path):
        raise HTTPException(status_code=404, detail="Todavía no hay ningún bulletin.json generado.")
    with open(bulletin_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/bulletin/run")
def run_bulletin_generation():
    try:
        subprocess.run(["python", "app/src/select_week.py"], check=True, cwd="/workspace")
        return {"message": "Borrador generado con éxito. Listo para revisión."}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error en la generación: {str(e)}")

@app.post("/api/news/manual")
def add_manual_news(news: ManualNewsInput):
    """Descarga la noticia a mano usando Trafilatura para extraer solo el artículo limpio."""
    try:
        # 1. Intentar descargar la URL con Trafilatura
        downloaded = trafilatura.fetch_url(news.url)
        
        # Si trafilatura falla por algún bloqueo, usamos un request normal como plan B
        if not downloaded:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            res = requests.get(news.url, headers=headers, timeout=15)
            res.raise_for_status()
            downloaded = res.text

        # 2. Extraer SOLO el texto útil y los metadatos (título)
        text_content = trafilatura.extract(downloaded)
        metadata = trafilatura.extract_metadata(downloaded)
        
        # Si metadata tiene título lo usamos, si no, intentamos con BeautifulSoup clásico
        if metadata and metadata.title:
            title = metadata.title
        else:
            soup = BeautifulSoup(downloaded, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.text.strip() if title_tag else news.url

        if not text_content:
            # Si trafilatura no saca texto, usamos BeautifulSoup a lo bruto como fallback
            soup = BeautifulSoup(downloaded, 'html.parser')
            for bad_tag in soup(["script", "style", "nav", "footer", "aside"]):
                bad_tag.decompose()
            text_content = soup.get_text(separator=" ", strip=True)
            
        # Limitar a 5000 caracteres para no ahogar al modelo IA
        text_content = text_content[:5000]

        content_hash = hashlib.sha256(text_content.encode("utf-8", errors="ignore")).hexdigest()
        raw_data = json.dumps({
            "source_type": "manual",
            "original_url": news.url,
            "method": "trafilatura"
        }, ensure_ascii=False)
        # 3. Guardar en BD como una noticia perfecta lista para el Analista
        db_url = os.environ.get("DATABASE_URL")
        now = datetime.now(timezone.utc)
        
        inserted_id = None
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Orain content_hash eta raw eremuak ere gehitzen ditugu
                cur.execute(
                    """
                    INSERT INTO items 
                    (topic, source_id, source_type, title, url, canonical_url, published_at, fetched_at, content_text, content_hash, raw, status, priority, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'ready', 100, ARRAY['manual'])
                    ON CONFLICT (topic, canonical_url) DO NOTHING
                    RETURNING id;
                    """,
                    (
                        news.topic, 
                        "manual_submission", 
                        "manual", 
                        title, 
                        news.url, 
                        news.url,
                        now, 
                        now, 
                        text_content,
                        content_hash, # Berria
                        raw_data      # Berria
                    )
                )
                result = cur.fetchone()
                if result:
                    inserted_id = result[0]
                conn.commit()
        
        if inserted_id:
            return {"message": f"¡Éxito! Noticia guardada y limpiada con ID {inserted_id}."}
        else:
            return {"message": "La noticia ya existía en la base de datos."}

    except Exception as e:
        print(f"❌ Error inyectando noticia manual: {e}")
        raise HTTPException(status_code=500, detail=f"No se pudo procesar la URL: {str(e)}")