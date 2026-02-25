# SKILL MODULE: Source Quality Validation
**Propósito:** Criterios estrictos para evaluar la muestra de artículos devuelta por `verify_rss_tool`.

## 🏆 SISTEMA DE TIERS (Niveles de Calidad)

### TIER 1: "Gold Standard" (APROBACIÓN INMEDIATA)
- **Fuentes:** Releases oficiales (Django Software Foundation, Plone Foundation), laboratorios de IA (DeepMind, OpenAI, Anthropic), arXiv, papers de universidades.
- **Indicadores:** Hablan de versiones (ej. "Django 5.1 release"), papers con abstract, benchmarks técnicos.

### TIER 2: "Senior Engineering" (APROBAR SI ES TÉCNICO)
- **Fuentes:** Blogs de empresas SaaS (ej. Vinta Software para Django, CodeSyntax para Plone, HuggingFace para IA), blogs personales de desarrolladores reconocidos.
- **Indicadores:** Incluyen fragmentos de código, hablan de arquitectura, optimización, rendimiento (performance) o escalabilidad.

### TIER 3: "Junk / Clickbait" (RECHAZO INMEDIATO)
- **Fuentes:** Medium genérico sin código, sitios de noticias tech mainstream (TechCrunch, Xataka), agregadores masivos, foros de soporte.
- **Indicadores:** Títulos como "Top 10 plugins", "El futuro de la IA", "Cómo instalar X en 5 minutos".

## 🛑 FLUJO DE DECISIÓN
Si al leer el feed con `verify_rss_tool` ves que el 50% o más de los artículos son TIER 3, **rechaza el feed completo**. No queremos contaminar la base de datos.