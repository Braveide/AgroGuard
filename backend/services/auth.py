import os
from dotenv import load_dotenv
from fastapi import HTTPException, Header
from typing import Annotated

# Load environment variables (fallback to .env)
load_dotenv()

API_SECRET_KEY = os.getenv("API_SECRET_KEY")
API_PUBLIC_KEY = os.getenv("API_PUBLIC_KEY")

def verify_api_key(x_api_key: Annotated[str, Header()]):
    """Verifica la clave secreta del API (uso interno)."""
    if not API_SECRET_KEY:
        raise HTTPException(status_code=500, detail="API secret not configured")
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

def verify_public_key(x_api_key: Annotated[str, Header()]):
    """Verifica la clave pública del API (uso por clientes)."""
    if not API_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="API public key not configured")
    if x_api_key != API_PUBLIC_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True