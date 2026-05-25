# AgroGuard

## Visión general
AgroGuard es una aplicación web para gestión de plagas que permite registrar, buscar (local y GBIF), identificar por imagen, visualizar en mapa, cambiar idioma (es, en, pt) y usar modos de accesibilidad (campo, lector de voz, daltonismo).

## Estructura del proyecto
```
/backend
  - main.py, models.py
  - routers/ (plagas.py, imagen.py, pdf.py)
  - services/ (auth.py, db_service.py, gbif_service.py, gemini_service.py)
/frontend
  - index.html
  - css/main.css
  - js/
      utils.js, api.js, ui.js, i18n.js, a11y.js, map.js, bootstrap.js, init.js
```

## Requisitos
- Python 3.12+ (probado con 3.14)
- Node/npm (solo si se quiere compilar Tailwind; la versión actual usa la CDN)
- SQLite (integrado y creado automáticamente)
- Opcional: `weasyprint` (`pip install weasyprint`) para generar PDFs, `supabase-py` si se prefiere Supabase.

## Variables de entorno (.env)
```
API_SECRET_KEY   # clave interna (reconocimiento de voz, etc.)
API_PUBLIC_KEY   # clave pública requerida por el frontend
SUPABASE_URL    # URL de Supabase (opcional)
SUPABASE_KEY    # Key de Supabase (opcional)
GEMINI_API_KEY  # token para la API de Gemini Vision
DB_PATH         # ruta al archivo SQLite (por defecto agroguard.db)
```
Si no se proporcionan `SUPABASE_URL` y `SUPABASE_KEY`, la aplicación usará SQLite local.

## Instalación
    git clone <url-del-repositorio>
    cd mi-proyecto
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # Linux/macOS
    source .venv/bin/activate
    pip install -r requirements.txt
    # opcional para PDF
    pip install weasyprint

## Ejecutar
    uvicorn backend.main:app --reload
Visitar http://localhost:8000 en el navegador.

## Uso del frontend
- **Cambiar pestaña**: `cambiarTab('consultar'|'imagen'|'registrar'|'mapa')`
- **Registrar**: rellenar formulario → botón guarda (`registrarPlaga()`).
- **Buscar**: escribir nombre y pulsar Enter (`buscarIntegral()`).
- **Identificar imagen**: arrastrar o capturar foto → proceso (`identificarImagen()`).
- **Mapa**: abrir pestaña *Mapa* → se cargan los focos (`cargarMapa()`).
- **Idioma**: selector → `cambiarIdioma(lang)`.
- **Accesibilidad**: modo campo, lector de voz y filtros daltonismo (funciones en `a11y.js`).

## API (FastAPI)
| Ruta | Método | Descripción |
|------|--------|-------------|
| /registrar               | POST | Añade una plaga (requiere header `x-api-key`). |
| /buscar_local/{nombre}   | GET  | Búsqueda en la base local. |
| /buscar_externo/{nombre} | GET  | Búsqueda en GBIF + iNaturalist. |
| /focos                   | GET  | Devuelve los focos con coordenadas (para el mapa). |
| /identificar_imagen       | POST (multipart) | Identifica una plaga a partir de una foto. |
| /pdf                     | GET  | Genera y descarga un PDF con el registro completo. |
| /                        | GET  | Sirve `index.html`. |
Todos los endpoints públicos requieren la clave pública (`x-api-key`).

## Licencia
MIT – ver el archivo `LICENSE` para más detalles.
