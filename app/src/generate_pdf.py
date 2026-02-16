import os
import json
import subprocess
import re
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

def escape_latex(s: str) -> str:
    """Escapa caracteres especiales de LaTeX para evitar errores de compilación."""
    if not s:
        return ""
    # Caracteres especiales: & % $ # _ { } ~ ^ \
    s = s.replace('\\', '\\textbackslash{}')
    s = re.sub(r'([&%$#_{}])', r'\\\1', s)
    s = s.replace('~', '\\textasciitilde{}')
    s = s.replace('^', '\\textasciicircum{}')
    return s

def main():
    json_path = os.environ.get("BULLETIN_OUT", "app/build/bulletin.json")
    build_dir = os.path.dirname(json_path)
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    tex_out_path = os.path.join(build_dir, "bulletin_compiled.tex")
    
    if not os.path.exists(json_path):
        raise SystemExit(f"No se encontró el archivo JSON en: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Configuramos Jinja2 para que no choque con las llaves de LaTeX
    env = Environment(
        loader=FileSystemLoader(template_dir),
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
        trim_blocks=True,
        autoescape=False
    )
    
    # Añadimos el filtro personalizado de LaTeX
    env.filters['escape_tex'] = escape_latex

    template = env.get_template("bulletin.tex")
    
    # Preparamos la fecha en formato legible
    gen_date = datetime.fromisoformat(data["generated_at"]).strftime("%d de %B, %Y")

    # Renderizamos la plantilla con los datos
    tex_content = template.render(
        topics=data.get("topics", {}),
        date=gen_date
    )

    # Guardamos el .tex
    with open(tex_out_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    print(f"✅ Archivo LaTeX generado en: {tex_out_path}")

    # Compilamos el PDF usando pdflatex
    print("Compilando PDF con LaTeX...")
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", build_dir, tex_out_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"🎉 ¡Éxito! PDF generado en: {os.path.join(build_dir, 'bulletin_compiled.pdf')}")
    except subprocess.CalledProcessError as e:
        print("❌ Error al compilar el PDF. Revisa los logs de LaTeX.")
        print(e.stdout.decode('utf-8', errors='ignore'))

if __name__ == "__main__":
    main()