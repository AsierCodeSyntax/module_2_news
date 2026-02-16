import os
import json
import time
import psycopg
import requests
import google.generativeai as genai

def evaluate_with_gemini(prompt: str, api_key: str) -> dict:
    genai.configure(api_key=api_key)
    # Usamos gemini-1.5-flash (el estándar actual rápido y barato)
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    response = model.generate_content(prompt)
    return json.loads(response.text)

def evaluate_with_ollama(prompt: str, url: str, model_name: str, api_key: str) -> dict:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    payload = {
        "model": model_name,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    
    endpoint = f"{url.rstrip('/')}/api/generate"
    response = requests.post(endpoint, json=payload, headers=headers)
    response.raise_for_status()
    
    # Ollama devuelve el string JSON dentro de la clave 'response'
    return json.loads(response.json()["response"])

def main():
    db_url = os.environ.get("DATABASE_URL")
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    
    if not db_url:
        raise SystemExit("DATABASE_URL no configurada.")

    with psycopg.connect(db_url) as conn:
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
            print("No hay items pendientes de evaluar por LLM.")
            return

        print(f"Enviando {len(rows)} items a [{provider.upper()}] para resumen y puntuación...")
        processed, errors = 0, 0

        for item_id, topic, title, content_text in rows:
            texto_truncado = content_text[:3000] if content_text else "(Sin contenido)"
            
            prompt = f"""
            Analiza este artículo técnico sobre '{topic}'.
            Título: {title}
            Contenido: {texto_truncado}
            
            Devuelve la respuesta ESTRICTAMENTE en este formato JSON:
            {{
                "summary": "Resumen técnico de máximo 2 líneas en español.",
                "score": <número entero del 1 al 10 evaluando su importancia para la industria>
            }}
            """

            try:
                if provider == "gemini":
                    api_key = os.environ.get("GEMINI_API_KEY")
                    result = evaluate_with_gemini(prompt, api_key)
                elif provider == "ollama":
                    url = os.environ.get("OLLAMA_API_URL")
                    model_name = os.environ.get("OLLAMA_MODEL", "llama3.1")
                    api_key = os.environ.get("OLLAMA_API_KEY", "")
                    result = evaluate_with_ollama(prompt, url, model_name, api_key)
                else:
                    raise ValueError(f"Proveedor desconocido: {provider}")
                
                summary = result.get("summary", "Sin resumen.")
                score = int(result.get("score", 0))

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
                
                processed += 1
                print(f"[{topic}] Evaluado OK | Nota: {score}/10 | {title[:50]}...")
                
                # Pausa para no saturar APIs
                time.sleep(2)

            except Exception as e:
                print(f"  ❌ Error procesando item {item_id}: {e}")
                errors += 1

        print(f"\n--- Resumen LLM ({provider.upper()}) ---")
        print(f"Procesados OK: {processed} | Errores: {errors}")

if __name__ == "__main__":
    main()