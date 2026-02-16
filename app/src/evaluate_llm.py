import os
import json
import time
import re
import psycopg
import requests
import google.generativeai as genai

def evaluate_with_gemini(prompt: str, api_key: str) -> dict:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        raise ValueError(f"Gemini no devolvió un JSON válido. Respuesta cruda: {response.text[:200]}")

def evaluate_with_ollama(prompt: str, url: str, model_name: str, api_key: str) -> dict:
    headers = {}
    if api_key and api_key != "Api":
        headers["Authorization"] = f"Bearer {api_key}"
        
    payload = {
        "model": model_name,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    
    base_url = url.rstrip('/')
    endpoint = f"{base_url}/generate" if base_url.endswith("/api") else f"{base_url}/api/generate"
        
    response = requests.post(endpoint, json=payload, headers=headers)
    
    if not response.ok:
        raise ValueError(f"Error HTTP {response.status_code}: {response.text[:200]}")
        
    try:
        data = response.json()
        raw_text = data["response"].strip()
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        return json.loads(raw_text)
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Error parseando respuesta de Ollama. Servidor devolvió: {response.text[:200]}")

def main():
    db_url = os.environ.get("DATABASE_URL")
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    
    if not db_url:
        raise SystemExit("DATABASE_URL no configurada.")

    total_processed = 0
    total_errors = 0

    with psycopg.connect(db_url) as conn:
        # BUCLE PARA PROCESAR TODA LA COLA
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, topic, title, coalesce(content_text,'') as content_text
                    FROM items
                    WHERE status='ready' AND qdrant_id IS NOT NULL
                    ORDER BY fetched_at ASC
                    LIMIT 100
                    """
                )
                rows = cur.fetchall()

            if not rows:
                break # Si no hay filas, salimos del bucle infinito

            print(f"\nProcesando lote de {len(rows)} items con [{provider.upper()}]...")

            for item_id, topic, title, content_text in rows:
                texto_truncado = content_text[:3000] if content_text else "(Sin contenido)"
                
                # PROMPT ACTUALIZADO: Float y Euskera
                prompt = f"""
                Analiza este artículo técnico sobre '{topic}'.
                Título: {title}
                Contenido: {texto_truncado}
                
                Devuelve la respuesta ESTRICTAMENTE en este formato JSON puro sin envoltorios markdown:
                {{
                    "summary": "Euskarazko laburpen teknikoa, gehienez 2 lerrotan (Resumen técnico en Euskera, máximo 2 líneas).",
                    "score": <número decimal (float) del 0.0 al 10.0 evaluando su importancia para la industria, por ejemplo 7.3>
                }}
                """

                try:
                    if provider == "gemini":
                        api_key = os.environ.get("GEMINI_API_KEY")
                        if not api_key:
                            raise ValueError("GEMINI_API_KEY no encontrada en .env")
                        result = evaluate_with_gemini(prompt, api_key)
                    elif provider == "ollama":
                        url = os.environ.get("OLLAMA_API_URL")
                        model_name = os.environ.get("OLLAMA_MODEL", "gemma3:12b")
                        api_key = os.environ.get("OLLAMA_API_KEY", "")
                        if not url:
                            raise ValueError("OLLAMA_API_URL no configurada en .env")
                        result = evaluate_with_ollama(prompt, url, model_name, api_key)
                    else:
                        raise ValueError(f"Proveedor desconocido: {provider}")
                    
                    summary = result.get("summary", "Ez dago laburpenik.")
                    # Aseguramos que sea FLOAT
                    score = float(result.get("score", 0.0))

                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE items 
                            SET summary_short=%s, llm_score=%s, status='evaluated' 
                            WHERE id=%s
                            """,
                            (summary, score, item_id)
                        )
                    conn.commit()
                    
                    total_processed += 1
                    print(f"[{topic}] OK | Nota: {score}/10 | {title[:45]}...")
                    time.sleep(2)

                except Exception as e:
                    print(f"  ❌ Error procesando item {item_id}: {e}")
                    total_errors += 1

    print(f"\n--- Resumen LLM ({provider.upper()}) ---")
    print(f"Procesados Totales OK: {total_processed} | Errores: {total_errors}")

if __name__ == "__main__":
    main()