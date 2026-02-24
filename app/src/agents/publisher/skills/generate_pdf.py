import os
import re
import shutil
import subprocess
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from langchain_core.tools import tool

def escape_tex(text):
    if not isinstance(text, str): return text
    tex_escapes = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    regex = re.compile('|'.join(re.escape(str(key)) for key in tex_escapes.keys()))
    return regex.sub(lambda match: tex_escapes[match.group(0)], text)

@tool
def generate_pdf_tool(news_data: dict) -> str:
    """Skill: Genera un boletín en PDF usando LaTeX y Jinja2."""
    print("📄 [Publisher Skill] Inyectando datos en LaTeX y compilando...")
    
    workspace_dir = "/workspace/app"
    templates_dir = os.path.join(workspace_dir, "src", "templates")
    build_dir = os.path.join(workspace_dir, "build")
    archive_dir = os.path.join(build_dir, "archive")
    
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(archive_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    tex_filename = f"{date_str}_techwatch_bulletin.tex"
    pdf_filename = f"{date_str}_techwatch_bulletin.pdf"
    
    tex_filepath = os.path.join(build_dir, tex_filename)
    pdf_build_path = os.path.join(build_dir, pdf_filename)
    pdf_final_path = os.path.join(archive_dir, pdf_filename)
    
    try:
        env = Environment(loader=FileSystemLoader(templates_dir), block_start_string='<%', block_end_string='%>', variable_start_string='<<', variable_end_string='>>', comment_start_string='<#', comment_end_string='#>')
        env.filters['escape_tex'] = escape_tex
        template = env.get_template("bulletin.tex")
        tex_content = template.render(date=date_str, topics=news_data.get("topics", {}))
        
        with open(tex_filepath, "w", encoding="utf-8") as f:
            f.write(tex_content)
    except Exception as e:
        return f"❌ Error en Jinja2: {e}"

    try:
        # Ejecutamos pdflatex. Quitamos el check=True para que no pete por simples advertencias
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_filename],
            cwd=build_dir,
            capture_output=True
        )
        
        # Comprobamos si el PDF realmente existe en la carpeta (esa es la prueba de fuego)
        if os.path.exists(pdf_build_path):
            import shutil
            shutil.move(pdf_build_path, pdf_final_path)
            return f"✅ Éxito. Usa exactamente esta ruta del archivo para enviarlo: {pdf_final_path}"
        else:
            # Si no existe, entonces sí que fue un error fatal
            log_error = result.stdout.decode('utf-8', errors='ignore')[-300:]
            return f"❌ Fallo fatal en pdflatex. No se creó el PDF. Logs: {log_error}"
            
    except Exception as e:
        return f"❌ Error de sistema al ejecutar pdflatex: {e}"