import os
import json
import subprocess
import re
import shutil  # <-- NUEVO IMPORT PARA COPIAR ARCHIVOS
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

def escape_latex(s: str) -> str:
    if not s:
        return ""
    s = s.replace('\\', '\\textbackslash{}')
    s = re.sub(r'([&%$#_{}])', r'\\\1', s)
    s = s.replace('~', '\\textasciitilde{}')
    s = s.replace('^', '\\textasciicircum{}')
    # 2. Map Greek letters to math mode (very common in AI papers)
    greek_map = {
        'α': r'$\alpha$', 'β': r'$\beta$', 'γ': r'$\gamma$', 'δ': r'$\delta$',
        'ε': r'$\epsilon$', 'ζ': r'$\zeta$', 'η': r'$\eta$', 'θ': r'$\theta$',
        'ι': r'$\iota$', 'κ': r'$\kappa$', 'λ': r'$\lambda$', 'μ': r'$\mu$',
        'ν': r'$\nu$', 'ξ': r'$\xi$', 'ο': r'$o$', 'π': r'$\pi$', 'ρ': r'$\rho$',
        'σ': r'$\sigma$', 'τ': r'$\tau$', 'υ': r'$\upsilon$', 'φ': r'$\phi$',
        'χ': r'$\chi$', 'ψ': r'$\psi$', 'ω': r'$\omega$', 'Δ': r'$\Delta$',
        'Γ': r'$\Gamma$', 'Θ': r'$\Theta$', 'Λ': r'$\Lambda$', 'Ξ': r'$\Xi$',
        'Π': r'$\Pi$', 'Σ': r'$\Sigma$', 'Φ': r'$\Phi$', 'Ψ': r'$\Psi$', 'Ω': r'$\Omega$'
    }
    for char, latex_equiv in greek_map.items():
        s = s.replace(char, latex_equiv)
        
    # 3. Strip dangerous Unicode characters (Emojis, non-Latin scripts)
    # Keeps ASCII, Latin-1 (ñ, accents), typographic quotes, and our injected math symbols
    s = re.sub(r'[^\u0000-\u00FF\u2013-\u2014\u2018-\u201D\u2026\$\\\{\}]', '', s)
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
    env.filters['escape_tex'] = escape_latex

    template = env.get_template("bulletin.tex")
    gen_date = datetime.fromisoformat(data["generated_at"]).strftime("%Y-%m-%d")

    tex_content = template.render(
        topics=data.get("topics", {}),
        date=gen_date
    )

    with open(tex_out_path, "w", encoding="utf-8") as f:
        f.write(tex_content)
    print(f"✅ Archivo LaTeX generado en: {tex_out_path}")

    print("Compilando PDF con LaTeX...")
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", build_dir, tex_out_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        pdf_out = os.path.join(build_dir, 'bulletin_compiled.pdf')
        print(f"🎉 ¡Éxito! PDF generado en: {pdf_out}")
        
        # --- SISTEMA DE ARCHIVO (BACKUPS) ---
        archive_dir = os.path.join(build_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        backup_path = os.path.join(archive_dir, f"bulletin_{gen_date}.pdf")
        
        shutil.copy2(pdf_out, backup_path)
        print(f"💾 Copia de seguridad guardada para el histórico en: {backup_path}")
        
    except subprocess.CalledProcessError as e:
        print("❌ Error al compilar el PDF. Revisa los logs de LaTeX.")
        print(e.stdout.decode('utf-8', errors='ignore'))

if __name__ == "__main__":
    main()