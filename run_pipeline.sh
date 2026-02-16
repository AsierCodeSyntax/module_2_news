#!/bin/bash
echo "🚀 Iniciando pipeline de TechWatch..."

# 1. Ingesta de fuentes RSS (Extrae lo nuevo de las webs)
docker compose run --rm app python app/src/ingest.py --topic plone
docker compose run --rm app python app/src/ingest.py --topic django
docker compose run --rm app python app/src/ingest.py --topic ai

# 2. Ingesta de fuentes Scraping (Noticias oficiales sin RSS)
docker compose run --rm app python app/src/ingest_scrape.py --topic plone
# (Añadirías aquí django o ai si tuvieran scraping en el sources.yaml)

# 3. Enriquecimiento Básico (Asigna tags, limpia, da prioridad inicial)
docker compose run --rm app python app/src/enrich.py

# 4. Deduplicación Semántica con Qdrant (Limpia el ruido)
docker compose run --rm app python app/src/embed.py

# 5. Evaluación, Resumen y Puntuación con LLM (La magia de la IA)
docker compose run --rm app python app/src/evaluate_llm.py

# 6. Selección Semanal (Genera el JSON con lo mejor de la semana)
docker compose run --rm app python app/src/select_week.py

# 7. Generación del Boletín (Crea el PDF final)
docker compose run --rm app python app/src/generate_pdf.py

echo "✅ Pipeline finalizado. Revisa app/build/bulletin_compiled.pdf"