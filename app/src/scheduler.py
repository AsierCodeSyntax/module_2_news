import schedule
import time
import subprocess
import os
import requests
# Asegurarnos de que estamos en el directorio correcto
WORKSPACE_DIR = "/workspace"

def trigger_n8n_webhook():
    webhook_url = "http://n8n:5678/webhook/enviar-boletin"
    #webhook_url = "http://n8n:5678/webhook-test/enviar-boletin"
    print(f"🔔 Avisando a n8n en {webhook_url}...")
    try:
        response = requests.post(webhook_url)
        if response.ok:
            print("✅ n8n notificado correctamente. Enviando email...")
        else:
            print(f"⚠️ n8n respondió con error: {response.status_code}")
    except Exception as e:
        print(f"❌ No se pudo conectar con n8n: {e}")

def run_command(cmd_list):
    try:
        print(f"\n🚀 Ejecutando: {' '.join(cmd_list)}")
        subprocess.run(cmd_list, check=True, cwd=WORKSPACE_DIR)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando {' '.join(cmd_list)}: {e}")

def daily_pipeline():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] INICIANDO PIPELINE DIARIO...")
    
    # 1. Ingestas RSS
    for topic in ["plone", "django", "ai"]:
        run_command(["python", "app/src/ingest.py", "--topic", topic])
        
    # 2. Ingestas Scraping (Noticias oficiales)
    run_command(["python", "app/src/ingest_scrape.py", "--topic", "plone"])
    
    # 3. Enriquecimiento y Agentes IA
    run_command(["python", "app/src/enrich.py"])
    run_command(["python", "app/src/process_news.py"]) # <--- Nuesto nuevo Orquestador
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] PIPELINE DIARIO COMPLETADO.")

def weekly_bulletin():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] INICIANDO GENERACIÓN DE BOLETÍN SEMANAL...")
    
    # 1. Seleccionar las mejores noticias y compilar el PDF
    run_command(["python", "app/src/select_week.py"])
    run_command(["python", "app/src/generate_pdf.py"])
    
    # 2. Aquí añadiremos el Webhook a n8n para que envíe el correo
    trigger_n8n_webhook() 
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BOLETÍN GENERADO.")

def main():
    print("🤖 TechWatch Scheduler Iniciado.")
    print("Configuración:")
    print(" - Ingesta y Evaluación: Todos los días a las 02:00 AM")
    print(" - Boletín PDF: Todos los viernes a las 08:00 AM")

    # Programación (ajusta las horas a tu gusto)
    schedule.every().day.at("02:00").do(daily_pipeline)
    schedule.every().friday.at("08:00").do(weekly_bulletin)

    # Bucle infinito que revisa si toca ejecutar algo
    while True:
        schedule.run_pending()
        time.sleep(60) # Comprueba cada minuto

if __name__ == "__main__":
    main()