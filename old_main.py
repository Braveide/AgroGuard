import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends
from typing import Annotated
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
    print("❌ ERROR CRÍTICO: GEMINI_API_KEY no está detectada en las variables del entorno.")
    # No lanzamos SystemExit de inmediato para permitir que el contenedor se mantenga vivo y reporte el estado en Render

# ─────────────────────────────────────────────
# Configuración de la aplicación
# ─────────────────────────────────────────────
app = FastAPI(
    title="AgroGuard API",
    description="Sistema de gestión y consulta de plagas agrícolas",
    version="1.0.0 (Producción Render)",
)

# CORS Seguro: Solo dominios específicos permitidos
ALLOWED_ORIGINS = [
    "https://agroguard-gules.vercel.app",  # Frontend en Vercel
    "http://localhost:5500",                 # Desarrollo local
    "http://127.0.0.1:5500",                 # Desarrollo local alternativo
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Solo métodos necesarios
    allow_headers=["Content-Type", "x-api-key"],     # Solo headers necesarios
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
    confianza: int | None = None  # mapped from data.get("confidence")
    foto_url: str | None = None
    wikipedia_url: str | None = None

# ─────────────────────────────────────────────
# Helpers y Seguridad
# ─────────────────────────────────────────────
def _partes_from_candidates(gemini_data: dict) -> list:
    """Extrae la lista de partes desde candidates."""
    try:
        return gemini_data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        return []

def _primer_texto(partes: list, skip_thought: bool = False) -> str:
    """Devuelve el primer texto no vacío de una lista de partes."""
    for parte in partes:
        if skip_thought and parte.get("thought", False):
            continue
        texto = parte.get("text", "").strip()
        if texto:
            return texto
    return ""

def extraer_texto_gemini(gemini_data: dict) -> str:
    # Intento 1: desde contents (respuesta directa)
    try:
        partes = gemini_data["contents"][0]["parts"]
        texto = _primer_texto(partes, skip_thought=True)
        if texto:
            return texto
    except (KeyError, IndexError, TypeError):
        pass
    # Intento 2: desde candidates
    partes = _partes_from_candidates(gemini_data)
    return _primer_texto(partes)

def verify_api_key(x_api_key: Annotated[str, Header()]):
    if not API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="API secret not configured")
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

def verify_public_key(x_api_key: Annotated[str, Header()]):
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
    dependencies=[Depends(verify_public_key)],
    responses={
        400: {"description": "Error en base de datos externa"},
        401: {"description": "API key inválida"},
        500: {"description": "Error interno del servidor"},
    }
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
        "longitud": plaga.longitud if plaga.longitud is not None else 0.0,
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
                longitud=float(datos_guardados.get("longitud", 0.0)) if datos_guardados.get("longitud") is not None else 0.0,
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
            longitud=plaga.longitud if plaga.longitud is not None else 0.0,
        )

# (El resto del archivo original sigue idéntico al anterior, truncado por brevedad)
