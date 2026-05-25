from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..models import RegistroPlaga, RespuestaPlaga
from ..services.auth import verify_public_key, verify_api_key
from ..services.db_service import get_connection
# Supabase client is created in main and passed via app.state? For simplicity we'll import from ..main
from ..main import supabase  # type: ignore

router = APIRouter(prefix="", tags=["Plagas"])

# -------------------- CRUD --------------------

@router.post(
    "/registrar",
    response_model=RespuestaPlaga,
    summary="Registra una nueva plaga en la bitácora",
    dependencies=[Depends(verify_public_key)],
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
        result = supabase.table("bitacora_plagas").insert(payload).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Supabase no devolvió datos")
        datos = result.data[0]
        return RespuestaPlaga(
            id=datos["id"],
            nombre_plaga=datos["nombre_plaga"],
            nombre_cientifico=datos["nombre_cientifico"],
            familia=datos.get("familia", datos.get("family", "")),
            reino=datos.get("reino", datos.get("kingdom", "")),
            riesgo=datos["riesgo"],
            ficha_tecnica=datos["ficha_tecnica"],
            fecha=str(datos["fecha"]),
            latitud=float(datos.get("latitud", 0.0)) if datos.get("latitud") is not None else 0.0,
            longitud=float(datos.get("longitud", 0.0)) if datos.get("longitud") is not None else 0.0,
        )
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bitacora_plagas (nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha, latitud, longitud)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plaga.nombre_plaga,
                plaga.nombre_cientifico,
                plaga.familia,
                plaga.reino,
                plaga.riesgo,
                plaga.ficha_tecnica,
                str(plaga.fecha),
                plaga.latitud,
                plaga.longitud,
            ),
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
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

@router.get(
    "/buscar_local/{nombre}",
    response_model=List[RespuestaPlaga],
    summary="Consulta registros locales por nombre de plaga",
)
async def buscar_local(nombre: str):
    rows = []
    if supabase:
        result = (
            supabase.table("bitacora_plagas")
            .select("*")
            .ilike("nombre_plaga", f"%{nombre}%")
            .order("fecha", desc=True)
            .execute()
        )
        for r in result.data:
            lat = r.get("latitud") if r.get("latitud") is not None else 0.0
            lng = r.get("longitud") if r.get("longitud") is not None else 0.0
            r["latitud"] = float(lat) if lat else 0.0
            r["longitud"] = float(lng) if lng else 0.0
            rows.append(r)
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM bitacora_plagas WHERE nombre_plaga LIKE ? ORDER BY fecha DESC",
            (f"%{nombre}%",),
        )
        for r in cursor.fetchall():
            d = dict(r)
            d["latitud"] = d.get("latitud") if d.get("latitud") is not None else 0.0
            d["longitud"] = d.get("longitud") if d.get("longitud") is not None else 0.0
            rows.append(d)
        conn.close()
    return [RespuestaPlaga(**r) for r in rows]

@router.get(
    "/focos",
    response_model=List[RespuestaPlaga],
    summary="Devuelve todos los registros con coordenadas para el mapa",
)
async def obtener_focos():
    rows = []
    if supabase:
        result = supabase.table("bitacora_plagas").select("*").order("fecha", desc=True).execute()
        for r in result.data:
            lat = r.get("latitud") if r.get("latitud") is not None else 0.0
            lng = r.get("longitud") if r.get("longitud") is not None else 0.0
            r["latitud"] = float(lat) if lat else 0.0
            r["longitud"] = float(lng) if lng else 0.0
            rows.append(r)
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bitacora_plagas ORDER BY fecha DESC")
        for r in cursor.fetchall():
            d = dict(r)
            d["latitud"] = d.get("latitud") if d.get("latitud") is not None else 0.0
            d["longitud"] = d.get("longitud") if d.get("longitud") is not None else 0.0
            rows.append(d)
        conn.close()
    return [RespuestaPlaga(**r) for r in rows]

@router.get(
    "/registros",
    response_model=List[RespuestaPlaga],
    summary="Lista todos los registros de la bitácora",
)
async def listar_registros():
    rows = []
    if supabase:
        result = supabase.table("bitacora_plagas").select("*").order("fecha", desc=True).execute()
        for r in result.data:
            lat = r.get("latitud") if r.get("latitud") is not None else 0.0
            lng = r.get("longitud") if r.get("longitud") is not None else 0.0
            r["latitud"] = float(lat) if lat else 0.0
            r["longitud"] = float(lng) if lng else 0.0
            rows.append(r)
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre_plaga, nombre_cientifico, familia, reino, riesgo, ficha_tecnica, fecha, latitud, longitud FROM bitacora_plagas ORDER BY fecha DESC"
        )
        for r in cursor.fetchall():
            d = dict(r)
            d["latitud"] = d.get("latitud") if d.get("latitud") is not None else 0.0
            d["longitud"] = d.get("longitud") if d.get("longitud") is not None else 0.0
            rows.append(d)
        conn.close()
    return [RespuestaPlaga(**r) for r in rows]

@router.put(
    "/actualizar/{id}",
    response_model=RespuestaPlaga,
    dependencies=[Depends(verify_public_key)],
)
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
        "longitud": plaga.longitud if plaga.longitud is not None else 0.0,
    }
    if supabase:
        exist = supabase.table("bitacora_plagas").select("id").eq("id", id).execute()
        if not exist.data:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        supabase.table("bitacora_plagas").update(payload).eq("id", id).execute()
        # Return updated record (simplified by fetching again)
        updated = supabase.table("bitacora_plagas").select("*").eq("id", id).execute()
        r = updated.data[0]
        return RespuestaPlaga(
            id=id,
            nombre_plaga=r["nombre_plaga"],
            nombre_cientifico=r["nombre_cientifico"],
            familia=r.get("familia", r.get("family", "")),
            reino=r.get("reino", r.get("kingdom", "")),
            riesgo=r["riesgo"],
            ficha_tecnica=r["ficha_tecnica"],
            fecha=str(r["fecha"]),
            latitud=float(r.get("latitud", 0.0)),
            longitud=float(r.get("longitud", 0.0)),
        )
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bitacora_plagas WHERE id = ?", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        cursor.execute(
            """
            UPDATE bitacora_plagas SET nombre_plaga=?, nombre_cientifico=?, familia=?, reino=?, riesgo=?, ficha_tecnica=?, fecha=?, latitud=?, longitud=? WHERE id=?
            """,
            (
                plaga.nombre_plaga,
                plaga.nombre_cientifico,
                plaga.familia,
                plaga.reino,
                plaga.riesgo,
                plaga.ficha_tecnica,
                str(plaga.fecha),
                plaga.latitud,
                plaga.longitud,
                id,
            ),
        )
        conn.commit()
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
            longitud=plaga.longitud if plaga.longitud is not None else 0.0,
        )

@router.delete(
    "/eliminar/{id}",
    dependencies=[Depends(verify_public_key)],
)
async def eliminar_plaga(id: int):
    if supabase:
        exist = supabase.table("bitacora_plagas").select("id").eq("id", id).execute()
        if not exist.data:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        supabase.table("bitacora_plagas").delete().eq("id", id).execute()
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bitacora_plagas WHERE id = ?", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        cursor.execute("DELETE FROM bitacora_plagas WHERE id = ?", (id,))
        conn.commit()
        conn.close()
    return {"mensaje": f"Registro #{id} eliminado correctamente."}