import os
import json
import subprocess
import requests
import psycopg
import trafilatura 
import hashlib
import yaml
import re
from datetime import datetime, timezone, timedelta
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
        subprocess.run(["python", "app/src/generate_pdf.py"], check=True, cwd="/workspace")
        
        return {"message": "Draft and PDF successfully generated. Ready for review."}
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
    

@app.post("/api/bulletin/send")
def send_bulletin_email():
    """Ejecuta el script que coge el PDF y lo manda por Gmail."""
    try:
        subprocess.run(["python", "app/src/send_manual_email.py"], check=True, cwd="/workspace")
        return {"message": "¡Correo enviado con éxito al destinatario!"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail="Error enviando el correo. Comprueba las credenciales en Docker.")
    
@app.post("/api/bulletin/discard/{item_id}")
def discard_news_item(item_id: int):
    """Marca una noticia como rechazada y regenera el boletín con la siguiente mejor."""
    try:
        # 1. Cambiar el estado en la base de datos a 'rejected'
        db_url = os.environ.get("DATABASE_URL")
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE items SET status = 'rejected' WHERE id = %s",
                    (item_id,)
                )
                conn.commit()

        # 2. Regenerar el JSON (Automáticamente cogerá el reemplazo si lo hay)
        subprocess.run(["python", "app/src/select_week.py"], check=True, cwd="/workspace")
        
        # 3. Regenerar el PDF
        subprocess.run(["python", "app/src/generate_pdf.py"], check=True, cwd="/workspace")

        return {"message": f"Noticia {item_id} descartada y boletín regenerado."}
        
    except Exception as e:
        print(f"❌ Error descartando noticia: {e}")
        raise HTTPException(status_code=500, detail=f"No se pudo descartar: {str(e)}")
    
@app.get("/api/archive")
def list_archived_bulletins():
    """Devuelve la lista de todos los PDFs guardados en el histórico."""
    archive_dir = "/workspace/app/build/archive"
    
    # Si la carpeta no existe aún (porque no se ha generado ningún histórico), devolvemos lista vacía
    if not os.path.exists(archive_dir):
        return {"pdfs": []}
        
    pdfs = []
    for filename in os.listdir(archive_dir):
        if filename.endswith(".pdf"):
            file_path = os.path.join(archive_dir, filename)
            # Extraemos la fecha del nombre del archivo (ej: bulletin_2026-02-27.pdf -> 2026-02-27)
            date_str = filename.replace("bulletin_", "").replace(".pdf", "")
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            pdfs.append({
                "id": filename,
                "filename": filename,
                "url": f"/static/archive/{filename}",
                "date": date_str,
                "size_mb": round(size_mb, 2)
            })
            
    # Ordenar de más reciente a más antiguo
    pdfs.sort(key=lambda x: x["date"], reverse=True)
    
    return {"pdfs": pdfs}

# --- MODELOS PARA RSS ---
class RSSSource(BaseModel):
    name: str
    url: str
    topic: str

def validate_rss_url(url: str) -> bool:
    """Comprueba de forma rápida si una URL devuelve un XML/RSS válido."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        content = res.text.lower()
        if "<?xml" in content or "<rss" in content or "<feed" in content:
            return True
        return False
    except:
        return False

@app.get("/api/sources")
def get_all_sources():
    """Lee y devuelve todas las fuentes del archivo YAML estructurado."""
    sources = []
    yaml_path = "/workspace/sources.yaml"
    
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
            # Navegar a la sección 'topics'
            topics = data.get("topics", {})
            for topic_name, topic_data in topics.items():
                if isinstance(topic_data, dict):
                    topic_sources = topic_data.get("sources", [])
                    # Iterar sobre la lista de diccionarios de fuentes
                    for src in topic_sources:
                        if isinstance(src, dict) and "url" in src:
                            sources.append({
                                "id": src.get("id", f"{topic_name}-{src['url']}"),
                                "name": src.get("name", src.get("id", "RSS Feed")),
                                "url": src["url"],
                                "topic": topic_name,
                                "status": "pending"
                            })
                    
    return {"sources": sources}

@app.post("/api/sources/validate")
def validate_single_source(source: RSSSource):
    """Valida una URL y devuelve si está viva o rota."""
    is_valid = validate_rss_url(source.url)
    if not is_valid:
        raise HTTPException(status_code=400, detail="La URL no parece ser un RSS válido o está caída.")
    return {"message": "RSS válido", "status": "valid"}

@app.post("/api/sources")
def add_new_source(source: RSSSource):
    """Añade una nueva fuente respetando la estructura del YAML."""
    if not validate_rss_url(source.url):
        raise HTTPException(status_code=400, detail="El enlace no es un RSS válido.")
        
    yaml_path = "/workspace/sources.yaml"
    data = {}
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
    if "topics" not in data:
        data["topics"] = {}
        
    topic_key = source.topic.lower()
    if topic_key not in data["topics"]:
        data["topics"][topic_key] = {"sources": []}
        
    if "sources" not in data["topics"][topic_key]:
        data["topics"][topic_key]["sources"] = []
        
    # Comprobar si la URL ya existe en este topic
    existing_urls = [s.get("url") for s in data["topics"][topic_key]["sources"] if isinstance(s, dict)]
    
    if source.url not in existing_urls:
        # Generar un ID limpio basado en el nombre (ej: "Mi Blog" -> "mi_blog")
        clean_id = re.sub(r'[^a-z0-9]', '_', source.name.lower())
        if not clean_id:
            clean_id = f"custom_rss_{len(existing_urls)}"
            
        new_source = {
            "id": clean_id,
            "type": "rss",
            "name": source.name,
            "url": source.url,
            "tags": ["custom"]
        }
        
        data["topics"][topic_key]["sources"].append(new_source)
        
        with open(yaml_path, "w", encoding="utf-8") as f:
            # sort_keys=False para que no nos desordene las propiedades del YAML
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
    return {"message": "Fuente guardada con éxito."}

@app.delete("/api/sources")
def delete_source(topic: str, url: str):
    """Elimina una fuente del YAML estructurado."""
    yaml_path = "/workspace/sources.yaml"
    
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        topic_key = topic.lower()
        if "topics" in data and topic_key in data["topics"] and "sources" in data["topics"][topic_key]:
            sources_list = data["topics"][topic_key]["sources"]
            
            # Filtramos para quedarnos con todas MENOS la que coincide con la URL
            new_sources_list = [s for s in sources_list if isinstance(s, dict) and s.get("url") != url]
            
            if len(sources_list) != len(new_sources_list):
                data["topics"][topic_key]["sources"] = new_sources_list
                with open(yaml_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
    return {"message": "Fuente eliminada con éxito."}

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Recopila estadísticas reales de la BBDD y YAMLs para el dashboard."""
    db_url = os.environ.get("DATABASE_URL")
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # 1. Contar fuentes activas en los YAMLs
    active_sources = 0
    for yaml_file in ["/workspace/sources.yaml", "/workspace/sources_ia.yaml"]:
        if os.path.exists(yaml_file):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "topics" in data:
                    for t, t_data in data["topics"].items():
                        if isinstance(t_data, dict) and "sources" in t_data:
                            active_sources += len(t_data["sources"])

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 2. KPIs de los últimos 7 días
            cur.execute("SELECT COUNT(*) FROM items WHERE fetched_at >= %s", (seven_days_ago,))
            ingested_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM items WHERE fetched_at >= %s AND llm_score >= 8", (seven_days_ago,))
            high_quality_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM items WHERE fetched_at >= %s AND 'manual' = ANY(tags)", (seven_days_ago,))
            manual_count = cur.fetchone()[0]

            # 3. Gráfico de Volumen (Últimos 7 días)
            cur.execute("""
                SELECT DATE(fetched_at), COUNT(*)
                FROM items
                WHERE fetched_at >= %s
                GROUP BY DATE(fetched_at)
            """, (seven_days_ago,))
            daily_counts = dict(cur.fetchall())

            ingestion_data = []
            for i in range(6, -1, -1):
                day_date = (now - timedelta(days=i)).date()
                day_name = day_date.strftime("%a") # Mon, Tue, etc.
                ingestion_data.append({
                    "day": day_name,
                    "articles": daily_counts.get(day_date, 0)
                })

            # 4. Calidad media por Topic
            cur.execute("""
                SELECT topic, AVG(llm_score)
                FROM items
                WHERE llm_score IS NOT NULL
                GROUP BY topic
            """)
            quality_data = [{"topic": row[0].upper() if row[0].lower() == 'ai' else row[0].title(), "score": round(row[1], 1)} for row in cur.fetchall()]

            # 5. Distribución de Origen
            cur.execute("SELECT source_type, COUNT(*) FROM items GROUP BY source_type")
            source_dist = []
            for row in cur.fetchall():
                s_type = row[0] or "unknown"
                name = "RSS" if s_type == "rss" else "Scrape" if s_type == "scrape" else "Manual" if s_type == "manual" else s_type.capitalize()
                source_dist.append({"name": name, "value": row[1]})
            if not source_dist:
                source_dist = [{"name": "Sin datos", "value": 1}] # Fallback seguro

            # 6. Top 3 Artículos del día/semana
            cur.execute("""
                SELECT id, title, topic, llm_score
                FROM items
                WHERE llm_score IS NOT NULL 
                ORDER BY llm_score DESC, published_at DESC
                LIMIT 3
            """)
            top_articles = []
            for row in cur.fetchall():
                top_articles.append({
                    "id": row[0],
                    "title": row[1],
                    "topic": row[2].upper() if row[2].lower() == 'ai' else row[2].title(),
                    "score": float(row[3])
                })

    return {
        "kpis": {
            "active_sources": active_sources,
            "ingested": ingested_count,
            "high_quality": high_quality_count,
            "manual": manual_count
        },
        "ingestion_data": ingestion_data,
        "quality_by_topic": quality_data,
        "source_distribution": source_dist,
        "top_articles": top_articles
    }