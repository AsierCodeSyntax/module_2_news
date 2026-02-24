import os
import smtplib
from email.message import EmailMessage
from langchain_core.tools import tool
from dotenv import load_dotenv # <-- 1. AÑADIMOS ESTA IMPORTACIÓN

# 2. CARGAMOS LAS VARIABLES ANTES DE EJECUTAR LA HERRAMIENTA
load_dotenv()

@tool
def send_gmail_tool(subject: str, body: str, attachment_path: str) -> str:
    """Skill: Envía un correo electrónico mediante Gmail con un archivo adjunto (PDF)."""
    
    # 0. Destinatario fijado por defecto
    recipient_email = "aiglesias@codesyntax.com"
    
    print(f"📧 [Publisher Skill] Preparando envío de correo a {recipient_email}...")
    
    # 1. Recuperar credenciales del entorno
    sender_email = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not sender_email or not app_password:
        return "❌ Error: Faltan las credenciales. Define GMAIL_ADDRESS y GMAIL_APP_PASSWORD en el entorno."
        
    # 2. Verificar que el PDF realmente exista antes de intentar enviarlo
    if not os.path.exists(attachment_path):
        return f"❌ Error: El archivo adjunto no existe en la ruta: {attachment_path}"
        
    try:
        # 3. Construir el mensaje
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg.set_content(body)
        
        # 4. Leer y adjuntar el PDF
        with open(attachment_path, 'rb') as f:
            pdf_data = f.read()
            pdf_name = os.path.basename(attachment_path)
            
        msg.add_attachment(
            pdf_data, 
            maintype='application', 
            subtype='pdf', 
            filename=pdf_name
        )
        
        # 5. Conectar a Gmail y enviar
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
            
        return f"✅ Correo enviado con éxito a {recipient_email} con el adjunto {pdf_name}"
        
    except Exception as e:
        return f"❌ Error de sistema al enviar el correo: {e}"