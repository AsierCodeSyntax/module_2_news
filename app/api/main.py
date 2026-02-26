import os
import json
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="TechWatch API", description="API para el Dashboard de React")

# Configurar CORS (Permite a React hacer peticiones a esta API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción pondremos aquí la URL de React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE DATOS (Pydantic) ---
class ManualNewsInput(BaseModel):
    url: str
    topic: str  # plone, django, ai

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "TechWatch API is running and ready! 🚀"}

@app.get("/api/bulletin/latest")
def get_latest_bulletin():
    """Devuelve el JSON del último borrador generado para que React lo pinte."""
    bulletin_path = "/workspace/app/build/bulletin.json"
    
    if not os.path.exists(bulletin_path):
        raise HTTPException(status_code=404, detail="Todavía no hay ningún bulletin.json generado.")
    
    with open(bulletin_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.post("/api/bulletin/run")
def run_bulletin_generation():
    """Ejecuta los scripts para generar un nuevo borrador del boletín."""
    try:
        # Aquí ejecutaremos el Publisher (lo separaremos del envío de email más adelante)
        subprocess.run(["python", "app/src/select_week.py"], check=True, cwd="/workspace")
        return {"message": "Borrador generado con éxito. Listo para revisión."}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error en la generación: {str(e)}")

@app.post("/api/news/manual")
def add_manual_news(news: ManualNewsInput):
    """Endpoint para inyectar noticias a mano desde React."""
    # En el siguiente paso meteremos aquí la lógica de scraping y guardado en DB
    return {"message": f"Recibida URL: {news.url} para el topic {news.topic.upper()}"}