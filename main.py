import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
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
# CARGAR VARIABLES DE ENTORNO (Adaptado para Render)
# ─────────────────────────────────────────────
load_dotenv()

# Prioriza las variables del sistema de Render, si no existen usa el fallback
PORT = int(os.environ.get("PORT", os.getenv("PORT", 8000)))
HOST = os.environ.get("HOST", os.getenv("HOST", "0.0.0.0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
DB_PATH = os.environ.get("DB_PATH", os.getenv("DB_PATH", "agroguard.db"))
ORIGEN_PERMITIDO = os.environ.get("ORIGEN_PERMITIDO", os.getenv("ORIGEN_PERMITIDO", "*"))
API_SECRET_KEY = os.environ.get("API_SECRET_KEY", os.getenv("API_SECRET_KEY"))
API_PUBLIC_KEY = os.environ.get("API_PUBLIC_KEY", os.getenv("API_PUBLIC_KEY"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))

# ─────────────────────────────────────────────
# VALIDACIÓN DE CONEXIÓN A SUPABASE
# ─────────────────────────────────────────────
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.table("bitacora_plagas").select("id").limit(1).execute()
        print("✅ Conexión inicial con Supabase establecida con éxito.")
    except Exception as e:
        print(f"⚠️ Supabase no disponible o no accesible de forma inicial: {e}")
        supabase = None

print("🚀 AgroGuard - Listo para Render")
print("✅ Variables de entorno procesadas:")
print(f"    PORT             → {PORT}")
print(f"    HOST             → {HOST}")
print(f"    ORIGEN_PERMITIDO → {ORIGEN_PERMITIDO}")
print(f"    GEMINI_API_KEY    → {'✅ CONFIGURADO' if GEMINI_API_KEY else '❌ NO ENCONTRADO'}")

# Validación segura para el despliegue en la nube
if not GEMINI_API_KEY:
    print("❌ ERROR CRÍTICO: GEMINI_API_KEY no detectada en las variables del entorno.")
    # No lanzamos SystemExit de inmediato para permitir que el contenedor se mantenga vivo y reporte el estado en Render

# ─────────────────────────────────────────────
# Configuración de la aplicación
# ─────────────────────────────────────────────
app = FastAPI(
    title="AgroGuard API",
    description="Sistema de gestión y consulta de plagas agrícolas",
    version="1.0.0 (Producción Render)",
)

# CORS Adaptivo: Permite localhost para pruebas y el dominio de tu frontend en Render
orígenes = ["*"] if ORIGEN_PERMITIDO == "*" else [ORIGEN_PERMITIDO, "http://localhost:5500", "http://127.0.0.1:5500"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=orígenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ─────────────────────────────────────────────
# Base de datos SQLite Local (Fallback de seguridad)
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
    ctnfianza: int | None = None  # Se mapeará con data.get("confidence")
    foto_url: str | None = None
    wikipedia_url: str | None = None

# ─────────────────────────────────────────────
# Helpers y Seguridad
# ─────────────────────────────────────────────
def extraer_texto_gemini(gemini_data: dict) -> str:
    try:
        partes = gemini_data["contents"][0]["parts"] if "contents" in gemini_data else gemini_data["candidates"][0]["content"]["parts"]
        for parte in partes:
            if parte.get("text") and not parte.get("thought", False):
                texto = parte["text"].strip()
                if texto: return texto
    except (KeyError, IndexError, TypeError):
        pass
    try:
        partes = gemini_data["candidates"][0]["content"]["parts"]
        for parte in partes:
            if parte.get("text"):
                texto = parte["text"].strip()
                if texto: return texto
    except (KeyError, IndexError, TypeError):
        pass
    return ""

def verify_api_key(x_api_key: str = Header(...)):
    if not API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="API secret not configured")
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

def verify_public_key(x_api_key: str = Header(...)):
    if not API_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="API public key not configured")
    if x_api_key != API_PUBLIC_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

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

def limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
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
# Endpoints de la API
# ─────────────────────────────────────────────

@app.post(
    "/registrar",
    response_model=RespuestaPlaga,
    summary="Registra una nueva plaga en la bitácora",
    tags=["Fase 3 – Persistencia"],
    dependencies=[Depends(verify_public_key)]
)
async def registrar_plaga(plaga: RegistroPlaga):
    payload = {
        "nombre_plaga": plaga.nombre_plaga,
        "nombre_cientifico": plaga.nombre_cientifico,
        "familia": plaga.familia,
        "reino": plaga.reino,
        "riesgo": plaga.riesgo,
        "ficha_tecnica": plaga.ficha_tecnica,
        "fecha": str(plaga.fecha),
        "latitud": plaga.latitud if plaga.latitud is not None else 0.0,
        "longitud": plaga.longitud if plaga.longitud is not None else 0.0
    }

    if supabase:
        try:
            result = supabase.table("bitacora_plagas").insert(payload).execute()
            if not result.data:
                raise HTTPException(status_code=500, detail="No se recibieron datos de vuelta desde Supabase.")
            datos_guardados = result.data[0]
            return RespuestaPlaga(
                id=datos_guardados["id"],
                nombre_plaga=datos_guardados["nombre_plaga"],
                nombre_cientifico=datos_guardados["nombre_cientifico"],
                familia=datos_guardados.get("familia", datos_guardados.get("family", "")),
                reino=datos_guardados.get("reino", datos_guardados.get("kingdom", "")),
                riesgo=datos_guardados["riesgo"],
                ficha_tecnica=datos_guardados["ficha_tecnica"],
                fecha=str(datos_guardados["fecha"]),
                latitud=float(datos_guardados.get("latitud", 0.0)) if datos_guardados.get("latitud") is not None else 0.0,
                longitud=float(datos_guardados.get("longitud", 0.0)) if datos_guardados.get("longitud") is not None else 0.0
            )
        except Exception as e:
            print(f"❌ Error al insertar en Supabase: {e}")
            raise HTTPException(status_code=400, detail=f"Error en base de datos externa: {str(e)}")
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
            latitud=plaga.latitud if plaga.latitud is not None else 0.0,
            longitud=plaga.longitud if plaga.longitud is not None else 0.0
        )

@app.get(
    "/buscar_externo/{nombre}",
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

    return {
        "nombre_cientifico": data.get("scientificName", "Desconocido"),
        "familia": data.get("family", "Desconocida"),
        "reino": data.get("kingdom", "Desconocido"),
        "confianza": data.get("confidence"),
        "foto_url": inaturalist["foto_url"],
        "wikipedia_url": inaturalist["wikipedia_url"],
    }

@app.get("/focos", response_model=list[RespuestaPlaga], summary="Devuelve todos los registros con coordenadas para el mapa", tags=["Geolocalización"])
async def obtener_focos():
    rows = []
    if supabase:
        try:
            result = supabase.table("bitacora_plagas").select("*").order("fecha", desc=True).execute()
            for r in result.data:
                lat = r.get("latitud") if r.get("latitud") is not None else r.get("lat", 0.0)
                lng = r.get("longitud") if r.get("longitud") is not None else r.get("lng", 0.0)
                
                r["latitud"] = float(lat) if lat else 0.0
                r["longitud"] = float(lng) if lng else 0.0
                r["familia"] = r.get("familia", r.get("family", "Desconocida"))
                r["reino"] = r.get("reino", r.get("kingdom", "Desconocido"))
                rows.append(r)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM bitacora_plagas ORDER BY fecha DESC")
            for r in cursor.fetchall():
                d = dict(r)
                d["latitud"] = d.get("latitud") if d.get("latitud") is not None else 0.0
                d["longitud"] = d.get("longitud") if d.get("longitud") is not None else 0.0
                rows.append(d)
        finally:
            conn.close()

    return [RespuestaPlaga(**r) for r in rows]

@app.get("/buscar_local/{nombre}", response_model=list[RespuestaPlaga], summary="Consulta registros locales por nombre de plaga", tags=["Fase 3 – Persistencia"])
async def consultar_plaga(nombre: str):
    rows = []
    if supabase:
        try:
            result = supabase.table("bitacora_plagas").select("*").ilike("nombre_plaga", f"%{nombre}%").order("fecha", desc=True).execute()
            if result.data:
                for r in result.data:
                    lat = r.get("latitud") if r.get("latitud") is not None else r.get("lat", 0.0)
                    lng = r.get("longitud") if r.get("longitud") is not None else r.get("lng", 0.0)
                    
                    r["latitud"] = float(lat) if lat else 0.0
                    r["longitud"] = float(lng) if lng else 0.0
                    r["familia"] = r.get("familia", r.get("family", "Desconocida"))
                    r["reino"] = r.get("reino", r.get("kingdom", "Desconocido"))
                    rows.append(r)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM bitacora_plagas WHERE nombre_plaga LIKE ? ORDER BY fecha DESC", (f"%{nombre}%",))
            for r in cursor.fetchall():
                d = dict(r)
                d["latitud"] = d.get("latitud") if d.get("latitud") is not None else 0.0
                d["longitud"] = d.get("longitud") if d.get("longitud") is not None else 0.0
                rows.append(d)
        finally:
            conn.close()

    return [RespuestaPlaga(**r) for r in rows]

@app.get("/registros", response_model=list[RespuestaPlaga], summary="Lista todos los registros de la bitácora", tags=["Fase 3 – Persistencia"])
async def listar_registros():
    rows = []
    if supabase:
        try:
            result = supabase.table("bitacora_plagas").select("*").order("fecha", desc=True).execute()
            for r in result.data:
                lat = r.get("latitud") if r.get("latitud") is not None else r.get("lat", 0.0)
                lng = r.get("longitud") if r.get("longitud") is not None else r.get("lng", 0.0)
                
                r["latitud"] = float(lat) if lat else 0.0
                r["longitud"] = float(lng) if lng else 0.0
                r["familia"] = r.get("familia", r.get("family", "Desconocida"))
                r["reino"] = r.get("reino", r.get("kingdom", "Desconocido"))
                rows.append(r)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha, latitud, longitud FROM bitacora_plagas ORDER BY fecha DESC")
            for r in cursor.fetchall():
                d = dict(r)
                d["latitud"] = d.get("latitud") if d.get("latitud") is not None else 0.0
                d["longitud"] = d.get("longitud") if d.get("longitud") is not None else 0.0
                rows.append(d)
        finally:
            conn.close()
    return [RespuestaPlaga(**r) for r in rows]

@app.put("/actualizar/{id}", response_model=RespuestaPlaga, summary="Actualiza un registro existente", tags=["Fase 3 – Persistencia"], dependencies=[Depends(verify_public_key)])
async def actualizar_plaga(id: int, plaga: RegistroPlaga):
    payload = {
        "nombre_plaga": plaga.nombre_plaga,
        "nombre_cientifico": plaga.nombre_cientifico,
        "familia": plaga.familia,
        "reino": plaga.reino,
        "riesgo": plaga.riesgo,
        "ficha_tecnica": plaga.ficha_tecnica,
        "fecha": str(plaga.fecha),
        "latitud": plaga.latitud if plaga.latitud is not None else 0.0,
        "longitud": plaga.longitud if plaga.longitud is not None else 0.0
    }
    if supabase:
        try:
            exist_res = supabase.table("bitacora_plagas").select("id").eq("id", id).execute()
            if not exist_res.data:
                raise HTTPException(status_code=404, detail=f"No existe un registro con id={id}.")
            supabase.table("bitacora_plagas").update(payload).eq("id", id).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM bitacora_plagas WHERE id = ?", (id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"No existe un registro con id={id}.")

            cursor.execute(
                "UPDATE bitacora_plagas SET nombre_plaga=?, nombre_cientifico=?, familia=?, reino=?, riesgo=?, ficha_tecnica=?, fecha=?, latitud=?, longitud=? WHERE id=?",
                (plaga.nombre_plaga, plaga.nombre_cientifico, plaga.familia, plaga.reino, plaga.riesgo, plaga.ficha_tecnica, str(plaga.fecha), plaga.latitud, plaga.longitud, id)
            )
            conn.commit()
        finally:
            conn.close()

    return RespuestaPlaga(
        id=id,
        nombre_plaga=plaga.nombre_plaga,
        nombre_cientifico=plaga.nombre_cientifico,
        familia=plaga.familia,
        reino=plaga.reino,
        riesgo=plaga.riesgo,
        ficha_tecnica=plaga.ficha_tecnica,
        fecha=str(plaga.fecha),
        latitud=plaga.latitud if plaga.latitud is not None else 0.0,
        longitud=plaga.longitud if plaga.longitud is not None else 0.0
    )

@app.delete("/eliminar/{id}", summary="Elimina un registro de la bitácora", tags=["Fase 3 – Persistencia"], dependencies=[Depends(verify_public_key)])
async def eliminar_plaga(id: int):
    if supabase:
        try:
            exist_res = supabase.table("bitacora_plagas").select("id").eq("id", id).execute()
            if not exist_res.data:
                raise HTTPException(status_code=404, detail=f"No existe un registro con id={id}.")
            supabase.table("bitacora_plagas").delete().eq("id", id).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
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
            raise HTTPException(status_code=422, detail="Gemini no pudo identificar la especie in the image.")

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
# Módulo Reporte PDF
# ─────────────────────────────────────────────
class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Reporte AgroGuard', ln=1, align='C')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1, align='C')
        self.ln(5)

    def footer(self):
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
    registros = []
    if supabase:
        try:
            result = supabase.table("bitacora_plagas").select("id,nombre_plaga,nombre_cientifico,familia,reino,riesgo,ficha_tecnica,fecha").order("fecha", desc=True).execute()
            registros = result.data
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha FROM bitacora_plagas ORDER BY fecha DESC")
            registros = [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    headers = ["ID", "Plaga", "Científico", "Familia", "Riesgo", "Fecha"]
    col_widths = [10, 30, 35, 30, 20, 30]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
    pdf.ln()
    
    pdf.set_font("Helvetica", size=9)
    fill = False
    pdf.set_fill_color(240, 240, 240)
    
    if registros:
        for r in registros:
            pdf.cell(col_widths[0], 6, limpiar_texto(str(r.get("id", ""))), border=1, fill=fill)
            pdf.cell(col_widths[1], 6, limpiar_texto(str(r.get("nombre_plaga", ""))), border=1, fill=fill)
            pdf.cell(col_widths[2], 6, limpiar_texto(str(r.get("nombre_cientifico", ""))), border=1, fill=fill)
            pdf.cell(col_widths[3], 6, limpiar_texto(str(r.get("familia", r.get("family", "")))), border=1, fill=fill)
            pdf.cell(col_widths[4], 6, limpiar_texto(str(r.get("riesgo", ""))), border=1, fill=fill)
            pdf.cell(col_widths[5], 6, limpiar_texto(str(r.get("fecha", ""))), border=1, fill=fill)
            pdf.ln()
            fill = not fill
    else:
        pdf.cell(0, 6, "No hay registros en la bitácora.", ln=1)

    #  fpdf2 genera los bytes directamente llamando al método limpio
    pdf_bytes = pdf.output()
    
    return Response(
        content=bytes(pdf_bytes),  # Aseguramos el formato binario correcto
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=AgroGuard_Reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"}
    )

@app.get("/config", tags=["Fase 1 - Configuración"])
async def check_config():
    return {
        "status": "Running in Cloud",
        "port": PORT,
        "host": HOST,
        "gemini_key_loaded": bool(GEMINI_API_KEY),
        "supabase_connected": bool(supabase),
        "version": "1.0.0 (Producción)"
    }

@app.get("/", tags=["General"])
def root():
    return {"sistema": "AgroGuard", "estado": "activo", "version": "1.0.0 (Desplegado en Render)"}

@app.get("/healthz", tags=["General"])
def healthz():
    return {"status": "ok"}