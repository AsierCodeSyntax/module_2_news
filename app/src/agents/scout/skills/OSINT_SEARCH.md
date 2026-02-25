# SKILL MODULE: OSINT & Advanced Search Tactics
**Propósito:** Técnicas avanzadas para encontrar feeds RSS técnicos que no están a simple vista.

## 🕵️‍♂️ OPERADORES Y 'DORKS' DE BÚSQUEDA
DuckDuckGo permite cierta lógica booleana. Usa estos patrones exactos en `search_web_tool`:

### Para encontrar Blogs de Ingeniería (Empresas Top):
- `[Tecnología] "engineering blog" (RSS OR Atom OR XML)`
  *Ejemplo:* `django "engineering blog" (RSS OR XML)`
- `site:github.io [Tecnología] "subscribe" RSS`

### Para encontrar Laboratorios y Papers (Especial para AI):
- `[Tema] research "papers" filetype:xml`
  *Ejemplo:* `"machine learning" research arXiv RSS`
- `[Tema] "technical report" (feed OR RSS)`

### Para encontrar Foros Core y Releases (Especial para Plone/Django):
- `[Tecnología] "release notes" RSS`
- `[Tecnología] "core developers" blog XML`

## ⚠️ ANTI-PATRONES DE BÚSQUEDA (Lo que NUNCA debes buscar)
- ❌ `[Tecnología] tutorial 2026` (Atrae SEO basura).
- ❌ `Qué es [Tecnología]` (Atrae contenido para juniors).
- ❌ `Noticias de [Tecnología]` (Demasiado genérico).

**Regla de Oro:** Tu query debe parecer escrita por un hacker buscando archivos de sindicación XML, no por un usuario normal buscando leer las noticias.