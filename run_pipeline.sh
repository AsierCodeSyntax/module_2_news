#!/bin/bash
echo "🚀 Iniciando ejecución manual completa de TechWatch..."

# =====================================================================
# OPCIÓN A: Ejecución mediante el Scheduler (Activa por defecto)
# =====================================================================
echo "--------------------------------------------------------"
echo "1️⃣ FASE DIARIA: Extracción, Vectorización y Traducción"
echo "--------------------------------------------------------"
docker compose run --rm app python -c "from app.src.scheduler import daily_pipeline; daily_pipeline()"

echo "--------------------------------------------------------"
echo "2️⃣ FASE SEMANAL: Generación de PDF, Backup y Envío"
echo "--------------------------------------------------------"
docker compose run --rm app python -c "from app.src.scheduler import weekly_bulletin; weekly_bulletin()"


# =====================================================================
# OPCIÓN B: Ejecución paso a paso (Descomentar para debugging)
# =====================================================================
# Si necesitas depurar un paso concreto, comenta la OPCIÓN A y 
# descomenta las líneas que necesites de aquí abajo:

# echo "1. Ingesta de fuentes RSS..."
# docker compose run --rm app python app/src/ingest.py --topic plone
# docker compose run --rm app python app/src/ingest.py --topic django
# docker compose run --rm app python app/src/ingest.py --topic ai

# echo "2. Ingesta de fuentes Scraping..."
# docker compose run --rm app python app/src/ingest_scrape.py --topic plone

# echo "3. Enriquecimiento Básico..."
# docker compose run --rm app python app/src/enrich.py

# echo "4. Deduplicación Semántica (Qdrant)..."
# docker compose run --rm app python app/src/embed.py

# echo "5. Evaluación y Traducción (IA)..."
# docker compose run --rm app python app/src/evaluate_llm.py

# echo "6. Selección Semanal..."
# docker compose run --rm app python app/src/select_week.py

# echo "7. Generación del Boletín (PDF)..."
# docker compose run --rm app python app/src/generate_pdf.py

# echo "8. Envío de Email (Webhook n8n)..."
# docker compose run --rm app python -c "from app.src.scheduler import trigger_n8n_webhook; trigger_n8n_webhook()"

echo "✅ Pipeline finalizado."