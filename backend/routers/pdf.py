from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Annotated
import os
import tempfile
# import weasyprint
from jinja2 import Template

from ..models import RespuestaPlaga
from ..services.auth import verify_public_key
from ..services.db_service import get_connection
from ..main import supabase

router = APIRouter(tags=["PDF"])

def _obtener_registros():
    rows = []
    if supabase:
        result = supabase.table("bitacora_plagas").select("*").order("fecha", desc=True).execute()
        for r in result.data:
            rows.append(r)
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bitacora_plagas ORDER BY fecha DESC")
        for r in cursor.fetchall():
            rows.append(dict(r))
        conn.close()
    return rows

@router.get(
    "/pdf",
    summary="Genera PDF con la bitácora de plagas",
    dependencies=[Depends(verify_public_key)],
)
async def generar_pdf():
    registros = _obtener_registros()
    if not registros:
        raise HTTPException(status_code=404, detail="No hay registros para generar PDF")
    # Plantilla HTML mínima
    html_template = """
    <html>
    <head>
        <meta charset='utf-8'>
        <style>
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #ddd; padding: 8px; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Bitácora de Plagas</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Nombre Plaga</th>
                    <th>Nombre Científico</th>
                    <th>Familia</th>
                    <th>Reino</th>
                    <th>Riesgo</th>
                    <th>Ficha Técnica</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody>
                {% for r in registros %}
                <tr>
                    <td>{{ r.id }}</td>
                    <td>{{ r.nombre_plaga }}</td>
                    <td>{{ r.nombre_cientifico }}</td>
                    <td>{{ r.familia }}</td>
                    <td>{{ r.reino }}</td>
                    <td>{{ r.riesgo }}</td>
                    <td>{{ r.ficha_tecnica }}</td>
                    <td>{{ r.fecha }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """
    rendered = Template(html_template).render(registros=registros)
    import weasyprint
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        weasyprint.HTML(string=rendered).write_pdf(tmp_pdf.name)
        pdf_path = tmp_pdf.name
    return FileResponse(pdf_path, media_type="application/pdf", filename="bitacora.pdf")