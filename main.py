import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
from datetime import date, datetime
import httpx
from supabase import create_client, Client
import base64
import io
from PIL import Image
from fpdf import FPDF
import sqlite3

# ─────────────────────────────────────────────
# CARGAR VARIABLES DE ENTORNO (Fase 1 - Obligatorio)
# ─────────────────────────────────────────────
load_dotenv()

# Variables desde .env
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = os.getenv("DB_PATH", "agroguard.db")
ORIGEN_PERMITIDO = os.getenv("ORIGEN_PERMITIDO")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
API_PUBLIC_KEY = os.getenv("API_PUBLIC_KEY")
# Supabase client (uso de la clave anónima)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Test a lightweight request to verify connectivity
        _test_conn = supabase.table("bitacora_plagas").select("id").limit(1).execute()
        if _test_conn.error:
            raise Exception(_test_conn.error.message)
    except Exception as exc:
        # Si la conexión falla, desactivar Supabase y usar SQLite
        print(f"⚠️ Supabase no disponible o no accesible: {exc}")
        supabase = None
else:
    supabase = None

# ─── BITÁCORA DE ERRORES (punto 4 del PDF) ───
print("🚀 AgroGuard - Fase 1 (Staging)")
print("✅ Variables de entorno cargadas correctamente:")
print(f"   PORT              → {PORT}")
print(f"   HOST              → {HOST}")
print(f"   DB_PATH           → {DB_PATH}")
print(f"   ORIGEN_PERMITIDO  → {ORIGEN_PERMITIDO}")
print(f"   GEMINI_API_KEY    → {'✅ CONFIGURADO' if GEMINI_API_KEY else '❌ NO ENCONTRADO'}")

if not GEMINI_API_KEY:
    print("❌ ERROR CRÍTICO: GEMINI_API_KEY no está en el archivo .env")
    raise SystemExit(1)

# ─────────────────────────────────────────────
# Configuración de la aplicación
# ─────────────────────────────────────────────
app = FastAPI(
    title="AgroGuard API",
    description="Sistema de gestión y consulta de plagas agrícolas",
    version="1.0.0 (Fase 1 - Staging)",
)

# CORS Configuración Total (Para solucionar el error de imágenes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ORIGEN_PERMITIDO] if ORIGEN_PERMITIDO else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ─────────────────────────────────────────────
# Base de datos SQLite (usa DB_PATH del .env)
# ─────────────────────────────────────────────
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bitacora_plagas (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_plaga      TEXT    NOT NULL,
            nombre_cientifico TEXT    NOT NULL,
            familia           TEXT    NOT NULL,
            reino             TEXT    NOT NULL,
            riesgo            TEXT    NOT NULL,
            ficha_tecnica     TEXT    NOT NULL,
            fecha             TEXT    NOT NULL,
            latitud           REAL,
            longitud          REAL
        )
    """)
    for col in ["latitud", "longitud"]:
        try:
            cursor.execute(f"ALTER TABLE bitacora_plagas ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────────
# Modelos Pydantic
# ─────────────────────────────────────────────
class RegistroPlaga(BaseModel):
    nombre_plaga: str
    nombre_cientifico: str
    familia: str
    reino: str
    riesgo: str
    ficha_tecnica: str
    fecha: date
    latitud: float | None = None
    longitud: float | None = None

class RespuestaPlaga(BaseModel):
    id: int
    nombre_plaga: str
    nombre_cientifico: str
    familia: str
    reino: str
    riesgo: str
    ficha_tecnica: str
    fecha: str
    latitud: float | None = None
    longitud: float | None = None

class RespuestaGBIF(BaseModel):
    nombre_cientifico: str
    familia: str
    reino: str
    confianza: int | None = None
    foto_url: str | None = None
    wikipedia_url: str | None = None

# ─────────────────────────────────────────────
# Helper: extraer texto de respuesta Gemini
# ─────────────────────────────────────────────
def extraer_texto_gemini(gemini_data: dict) -> str:
    try:
        partes = gemini_data["candidates"][0]["content"]["parts"]
        for parte in partes:
            if parte.get("text") and not parte.get("thought", False):
                texto = parte["text"].strip()
                if texto:
                    return texto
        for parte in partes:
            if parte.get("text"):
                texto = parte["text"].strip()
                if texto:
                    return texto
    except (KeyError, IndexError, TypeError):
        pass
    return ""
# ─────────────────────────────────────────────
# Seguridad: verificación de API key
# ─────────────────────────────────────────────
def verify_api_key(x_api_key: str = Header(...)):
    if not API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="API secret not configured")
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# ─────────────────────────────────────────────
# Seguridad: verificación de API key pública (para acciones de usuarios)
# ─────────────────────────────────────────────
def verify_public_key(x_api_key: str = Header(...)):
    if not API_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="API public key not configured")
    if x_api_key != API_PUBLIC_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# ─────────────────────────────────────────────
# iNaturalist helper
# ─────────────────────────────────────────────
async def traducir_con_inaturalist(nombre: str, client: httpx.AsyncClient) -> dict:
    resultado = {"nombre": nombre, "foto_url": None, "wikipedia_url": None}
    try:
        resp = await client.get(
            "https://api.inaturalist.org/v1/taxa",
            params={"q": nombre, "locale": "es", "per_page": 1, "rank": "species,genus,family,order"},
            timeout=8.0,
        )
        resp.raise_for_status()
        resultados = resp.json().get("results", [])
        if resultados:
            taxon = resultados[0]
            resultado["nombre"] = taxon.get("name", nombre)
            resultado["wikipedia_url"] = taxon.get("wikipedia_url")
            foto = taxon.get("default_photo")
            if foto:
                resultado["foto_url"] = foto.get("medium_url")
    except Exception:
        pass
    return resultado

# ─────────────────────────────────────────────
# Endpoint externo (iNaturalist → GBIF)
# ─────────────────────────────────────────────
@app.get(
    "/buscar_externo/{nombre}",
    response_model=RespuestaGBIF,
    summary="Consulta ficha científica (iNaturalist → GBIF)",
    tags=["Fase 2 – API Externa"],
)
async def buscar_externo(nombre: str):
    async with httpx.AsyncClient(timeout=12.0) as client:
        inaturalist = await traducir_con_inaturalist(nombre, client)
        nombre_cientifico_traducido = inaturalist["nombre"]

        try:
            response = await client.get(
                "https://api.gbif.org/v1/species/match",
                params={"name": nombre_cientifico_traducido, "verbose": False},
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"No se pudo contactar GBIF: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Error GBIF: {exc.response.text}")

    data = response.json()

    if data.get("matchType") == "NONE" or "scientificName" not in data:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró información para '{nombre}' (buscado como '{nombre_cientifico_traducido}').",
        )

    return RespuestaGBIF(
        nombre_cientifico=data.get("scientificName", "Desconocido"),
        familia=data.get("family", "Desconocida"),
        reino=data.get("kingdom", "Desconocido"),
        confianza=data.get("confidence"),
        foto_url=inaturalist["foto_url"],
        wikipedia_url=inaturalist["wikipedia_url"],
    )

# ─────────────────────────────────────────────
# Endpoints de persistencia (sin cambios)
# ─────────────────────────────────────────────
@app.post("/registrar", response_model=RespuestaPlaga, status_code=201, summary="Registra una plaga en la bitácora", tags=["Fase 3 – Persistencia"], dependencies=[Depends(verify_public_key)])
def registrar_plaga(plaga: RegistroPlaga):
    # Si Supabase está configurado, usarlo; de lo contrario, usar SQLite local
    if supabase:
        payload = {
            "nombre_plaga": plaga.nombre_plaga,
            "nombre_cientifico": plaga.nombre_cientifico,
            "familia": plaga.familia,
            "reino": plaga.reino,
            "riesgo": plaga.riesgo,
            "ficha_tecnica": plaga.ficha_tecnica,
            "fecha": str(plaga.fecha),
            "latitud": plaga.latitud,
            "longitud": plaga.longitud,
        }
        result = supabase.table("bitacora_plagas").insert(payload).execute()
        if result.error:
            raise HTTPException(status_code=500, detail=result.error.message)
        nuevo_id = result.data[0]["id"]
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO bitacora_plagas (nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha, latitud, longitud)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (plaga.nombre_plaga, plaga.nombre_cientifico, plaga.familia, plaga.reino, plaga.riesgo, plaga.ficha_tecnica, str(plaga.fecha), plaga.latitud, plaga.longitud)
            )
            conn.commit()
            nuevo_id = cursor.lastrowid
        finally:
            conn.close()

    return RespuestaPlaga(
        id=nuevo_id,
        nombre_plaga=plaga.nombre_plaga,
        nombre_cientifico=plaga.nombre_cientifico,
        familia=plaga.familia,
        reino=plaga.reino,
        riesgo=plaga.riesgo,
        ficha_tecnica=plaga.ficha_tecnica,
        fecha=str(plaga.fecha),
        latitud=plaga.latitud,
        longitud=plaga.longitud,
    )

# (Los demás endpoints /focos, /consultar, /registros, /actualizar, /eliminar se mantienen exactamente igual que en tu versión original)

@app.get("/focos", response_model=list[RespuestaPlaga], summary="Devuelve todos los registros con coordenadas para el mapa", tags=["Geolocalización"])
def obtener_focos():
    # Usar Supabase si está disponible; de lo contrario, SQLite local
    if supabase:
        result = supabase.table("bitacora_plagas").select("*").order("fecha", desc=True).execute()
        if result.error:
            raise HTTPException(status_code=500, detail=result.error.message)
        # Filtrar registros con latitud y longitud no nulas
        rows = [r for r in result.data if r.get("latitud") is not None and r.get("longitud") is not None]
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha, latitud, longitud
                FROM bitacora_plagas
                WHERE latitud IS NOT NULL AND longitud IS NOT NULL
                ORDER BY fecha DESC
            """)
            rows = cursor.fetchall()
        finally:
            conn.close()

    return [RespuestaPlaga(**dict(r) if isinstance(r, sqlite3.Row) else r) for r in rows]

@app.get("/consultar/{nombre}", response_model=list[RespuestaPlaga], summary="Consulta registros locales por nombre de plaga", tags=["Fase 3 – Persistencia"])
def consultar_plaga(nombre: str):
    # Si Supabase está disponible, usarlo; de lo contrario, usar SQLite
    if supabase:
        result = supabase.table("bitacora_plagas").select("*").ilike("nombre_plaga", f"%{nombre}%").order("fecha", desc=True).execute()
        if result.error:
            raise HTTPException(status_code=500, detail=result.error.message)
        rows = result.data
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM bitacora_plagas WHERE nombre_plaga LIKE ? ORDER BY fecha DESC", (f"%{nombre}%",))
            rows = cursor.fetchall()
        finally:
            conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros locales para '{nombre}'.")

    # rows may be sqlite3.Row or dict; normalize
    return [RespuestaPlaga(**dict(r) if isinstance(r, sqlite3.Row) else r) for r in rows]

@app.get("/registros", response_model=list[RespuestaPlaga], summary="Lista todos los registros de la bitácora", tags=["Fase 3 – Persistencia"])
def listar_registros():
    # Usar Supabase si está configurado
    if supabase:
        result = supabase.table("bitacora_plagas").select("id,nombre_plaga,nombre_cientifico,familia,reino,riesgo,ficha_tecnica,fecha").order("fecha", desc=True).execute()
        if result.error:
            raise HTTPException(status_code=500, detail=result.error.message)
        rows = result.data
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha FROM bitacora_plagas ORDER BY fecha DESC")
            rows = cursor.fetchall()
        finally:
            conn.close()
    # Normalizar filas
    return [RespuestaPlaga(**dict(r) if isinstance(r, sqlite3.Row) else r) for r in rows]

@app.put("/actualizar/{id}", response_model=RespuestaPlaga, summary="Actualiza un registro existente", tags=["Fase 3 – Persistencia"], dependencies=[Depends(verify_public_key)])
def actualizar_plaga(id: int, plaga: RegistroPlaga):
    # Si Supabase está disponible, usarlo; de lo contrario, usar SQLite
    if supabase:
        # Verificar existencia
        exist_res = supabase.table("bitacora_plagas").select("id").eq("id", id).execute()
        if exist_res.error:
            raise HTTPException(status_code=500, detail=exist_res.error.message)
        if not exist_res.data:
            raise HTTPException(status_code=404, detail=f"No existe un registro con id={id}.")
        # Actualizar registro
        payload = {
            "nombre_plaga": plaga.nombre_plaga,
            "nombre_cientifico": plaga.nombre_cientifico,
            "familia": plaga.familia,
            "reino": plaga.reino,
            "riesgo": plaga.riesgo,
            "ficha_tecnica": plaga.ficha_tecnica,
            "fecha": str(plaga.fecha),
        }
        update_res = supabase.table("bitacora_plagas").update(payload).eq("id", id).execute()
        if update_res.error:
            raise HTTPException(status_code=500, detail=update_res.error.message)
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM bitacora_plagas WHERE id = ?", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"No existe un registro con id={id}.")

            cursor.execute(
                "UPDATE bitacora_plagas SET nombre_plaga=?, nombre_cientifico=?, familia=?, reino=?, riesgo=?, ficha_tecnica=?, fecha=? WHERE id=?",
                (plaga.nombre_plaga, plaga.nombre_cientifico, plaga.familia, plaga.reino, plaga.riesgo, plaga.ficha_tecnica, str(plaga.fecha), id)
            )
            conn.commit()
        finally:
            conn.close()

    return RespuestaPlaga(id=id, **plaga.model_dump())

@app.delete("/eliminar/{id}", summary="Elimina un registro de la bitácora", tags=["Fase 3 – Persistencia"], dependencies=[Depends(verify_public_key)])
def eliminar_plaga(id: int):
    # Eliminar usando Supabase si está disponible
    if supabase:
        # Verificar existencia
        exist_res = supabase.table("bitacora_plagas").select("id").eq("id", id).execute()
        if exist_res.error:
            raise HTTPException(status_code=500, detail=exist_res.error.message)
        if not exist_res.data:
            raise HTTPException(status_code=404, detail=f"No existe un registro con id={id}.")
        # Eliminar
        del_res = supabase.table("bitacora_plagas").delete().eq("id", id).execute()
        if del_res.error:
            raise HTTPException(status_code=500, detail=del_res.error.message)
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM bitacora_plagas WHERE id = ?", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"No existe un registro con id={id}.")
            cursor.execute("DELETE FROM bitacora_plagas WHERE id = ?", (id,))
            conn.commit()
        finally:
            conn.close()
    return {"mensaje": f"Registro #{id} eliminado correctamente."}

# ─────────────────────────────────────────────
# Identificación por imagen (Gemini + iNaturalist + GBIF)
# ─────────────────────────────────────────────
@app.post(
    "/identificar_imagen",
    response_model=RespuestaGBIF,
    summary="Identifica una plaga desde una imagen usando Gemini Vision",
    tags=["Fase 2B – Imagen"],
    dependencies=[Depends(verify_api_key)],
)
async def identificar_imagen(imagen: UploadFile = File(...)):
    contenido = await imagen.read()
    try:
        img = Image.open(io.BytesIO(contenido)).convert("RGB")
        img.thumbnail((800, 800), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        contenido_comprimido = buffer.getvalue()
    except Exception:
        contenido_comprimido = contenido

    imagen_b64 = base64.b64encode(contenido_comprimido).decode("utf-8")

    async with httpx.AsyncClient(timeout=45.0) as client:
        gemini_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Identify the insect, pest or plant species in this image. Reply ONLY with the most likely scientific name (genus and species). If uncertain, reply with just the genus or family name. No explanations, just the scientific name."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": imagen_b64}}
                ]
            }],
            "generationConfig": {"maxOutputTokens": 50, "temperature": 0.1}
        }

        gemini_resp = await client.post(gemini_url, json=payload)
        gemini_resp.raise_for_status()
        gemini_data = gemini_resp.json()

        nombre_detectado = extraer_texto_gemini(gemini_data)

        if not nombre_detectado:
            raise HTTPException(status_code=422, detail="Gemini no pudo identificar la especie en la imagen.")

        inaturalist = await traducir_con_inaturalist(nombre_detectado, client)
        nombre_cientifico_final = inaturalist["nombre"]

        gbif_resp = await client.get("https://api.gbif.org/v1/species/match", params={"name": nombre_cientifico_final, "verbose": False})
        gbif_resp.raise_for_status()
        gbif_data = gbif_resp.json()

    if gbif_data.get("matchType") == "NONE" or "scientificName" not in gbif_data:
        raise HTTPException(status_code=404, detail=f"Gemini detectó '{nombre_detectado}' pero no se encontró en GBIF.")

    return RespuestaGBIF(
        nombre_cientifico=gbif_data.get("scientificName", nombre_detectado),
        familia=gbif_data.get("family", "Desconocida"),
        reino=gbif_data.get("kingdom", "Desconocido"),
        confianza=gbif_data.get("confidence"),
        foto_url=inaturalist["foto_url"],
        wikipedia_url=inaturalist["wikipedia_url"],
    )

# ─────────────────────────────────────────────
# Reporte PDF (sin cambios)
# ─────────────────────────────────────────────
def limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    # Reemplazos de caracteres especiales
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U',
        '–': '-', '—': '-', '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '°': ' ', '©': '(c)', '®': '(R)', '€': 'EUR',
    }
    for orig, reemplazo in reemplazos.items():
        texto = texto.replace(orig, reemplazo)
    return texto.encode('latin-1', errors='replace').decode('latin-1')

# ─────────────────────────────────────────────
# Seguridad: verificación de API key
# ─────────────────────────────────────────────
def verify_api_key(x_api_key: str = Header(...)):
    if not API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="API secret not configured")
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Removed misplaced decorator
class PDFReport(FPDF):
    def header(self):
        # Logo opcional: si tienes un archivo logo.png en la raíz, descomenta la línea siguiente
        # self.image('logo.png', x=10, y=8, w=20)
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Reporte AgroGuard', ln=1, align='C')
        # Fecha de generación
        self.set_font('Helvetica', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1, align='C')
        self.ln(5)

    def footer(self):
        # Posicionar a 1.5 cm del fondo
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Página {self.page_no()}', align='C')

@app.get(
    "/reporte_pdf",
    summary="Genera un reporte PDF de la bitácora",
    tags=["Reportes"],

)
def generar_reporte_pdf():
    # Recuperar datos usando Supabase si está configurado, de lo contrario usar SQLite
    if supabase:
        result = supabase.table("bitacora_plagas").select("id,nombre_plaga,nombre_cientifico,familia,reino,riesgo,ficha_tecnica,fecha").order("fecha", desc=True).execute()
        if result.error:
            raise HTTPException(status_code=500, detail=result.error.message)
        registros = result.data
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha FROM bitacora_plagas ORDER BY fecha DESC")
            registros = cursor.fetchall()
        finally:
            conn.close()

    # Utilizamos la clase PDFReport que incluye encabezado y pie de página
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    # Encabezado de tabla (el título ya lo agrega el header)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    headers = ["ID", "Plaga", "Científico", "Familia", "Riesgo", "Fecha"]
    col_widths = [10, 30, 35, 30, 20, 30]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
    pdf.ln()
    # Cuerpo de tabla con filas alternas
    pdf.set_font("Helvetica", size=9)
    fill = False
    pdf.set_fill_color(240, 240, 240)
    if registros:
        for r in registros:
            pdf.cell(col_widths[0], 6, str(r["id"]), border=1, fill=fill)
            pdf.cell(col_widths[1], 6, str(r["nombre_plaga"]), border=1, fill=fill)
            pdf.cell(col_widths[2], 6, str(r["nombre_cientifico"]), border=1, fill=fill)
            pdf.cell(col_widths[3], 6, str(r["familia"]), border=1, fill=fill)
            pdf.cell(col_widths[4], 6, str(r["riesgo"]), border=1, fill=fill)
            pdf.cell(col_widths[5], 6, str(r["fecha"]), border=1, fill=fill)
            pdf.ln()
            fill = not fill
    else:
        pdf.cell(0, 6, "No hay registros en la bitácora.", ln=1)

    pdf_output = pdf.output(dest='S')
    pdf_bytes = pdf_output.encode('latin-1')
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=AgroGuard_Reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"}
    )

# ─────────────────────────────────────────────
# ENDPOINT /config (Obligatorio del PDF)
# ─────────────────────────────────────────────
@app.get("/config", tags=["Fase 1 - Configuración"])
async def check_config():
    return {
        "status": "Running in Staging",
        "port": PORT,
        "host": HOST,
        "db_path": DB_PATH,
        "gemini_key_loaded": bool(GEMINI_API_KEY),
        "cors_origin": ORIGEN_PERMITIDO,
        "version": "1.0.0 (Fase 1 completada)"
    }

# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────
@app.get("/", tags=["General"])
def root():
    return RedirectResponse(url="/ui/")
@app.get("/healthz", tags=["General"])
def healthz():
    return {"status":"ok"}

# Serve UI (index.html) under /ui/
@app.get("/ui/", response_class=HTMLResponse)
async def serve_ui():
    return FileResponse("index.html", media_type="text/html")

# Ensure /ui (without trailing slash) also works
@app.get("/ui", include_in_schema=False)
def ui_redirect():
    return RedirectResponse(url="/ui/")