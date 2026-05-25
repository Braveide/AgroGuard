import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def build_gemini_url() -> str:
    """Construye la URL de la API Gemini usando la clave configurada."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no está configurada")
    return f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

def extraer_texto_gemini(gemini_data: dict) -> str:
    """Extrae el texto más relevante de la respuesta de Gemini.
    Se intentan dos estrategias: contenido directo y candidates."""
    # Intento 1: contenido directo
    try:
        partes = gemini_data["contents"][0]["parts"]
        for parte in partes:
            if parte.get("text") and not (parte.get("thought") if part.get("thought") else False):
                txt = parte["text"].strip()
                if txt:
                    return txt
    except Exception:
        pass
    # Intento 2: candidates
    try:
        partes = gemini_data["candidates"][0]["content"]["parts"]
        for parte in partes:
            txt = parte.get("text", "").strip()
            if txt:
                return txt
    except Exception:
        pass
    return ""