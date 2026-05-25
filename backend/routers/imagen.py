from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Annotated
import httpx
import os
import tempfile

from ..models import RespuestaGBIF
from ..services.auth import verify_api_key
from ..services.gemini_service import build_gemini_url, extraer_texto_gemini
from ..services.gbif_service import traducir_con_inaturalist, buscar_gbif_match

router = APIRouter(tags=["Imagen"])

@router.post(
    "/identificar_imagen",
    response_model=RespuestaGBIF,
    dependencies=[Depends(verify_api_key)],
    summary="Identifica una plaga a partir de una imagen",
)
async def identificar_imagen(imagen: UploadFile = File(...)) -> RespuestaGBIF:
    # Guardar temporalmente la imagen para poder enviarla como file multipart
    suffix = os.path.splitext(imagen.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await imagen.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        async with httpx.AsyncClient() as client:
            # Llamada a Gemini
            url_gemini = build_gemini_url()
            files = {"file": (imagen.filename, open(tmp_path, "rb"), imagen.content_type)}
            gemini_resp = await client.post(url_gemini, files=files, timeout=20)
            gemini_resp.raise_for_status()
            gemini_data = gemini_resp.json()
            # Extraer descripción textual
            descripcion = extraer_texto_gemini(gemini_data)
            if not descripcion:
                raise HTTPException(status_code=500, detail="Gemini no devolvió una descripción válida")
            # Traducción y datos complementarios vía iNaturalist
            info_inat = await traducir_con_inaturalist(descripcion, client)
            nombre_cientifico = info_inat.get("nombre", descripcion)
            # Consulta GBIF para obtener taxonomía y confianza
            gbif_match = await buscar_gbif_match(nombre_cientifico, client)
            # Construir respuesta unificada
            respuesta = {
                "nombre_cientifico": nombre_cientifico,
                "familia": gbif_match.get("family"),
                "reino": gbif_match.get("kingdom"),
                "confianza": gbif_match.get("confidence"),
                "foto_url": info_inat.get("foto_url"),
                "wikipedia_url": info_inat.get("wikipedia_url"),
            }
            return RespuestaGBIF(**respuesta)
    finally:
        # Limpiar archivo temporal
        try:
            os.remove(tmp_path)
        except Exception:
            pass