import httpx

async def traducir_con_inaturalist(nombre: str, client: httpx.AsyncClient) -> dict:
    """Traduce un nombre de especie usando la API de iNaturalist.
    Devuelve un dict con 'nombre' (nombre científico), 'foto_url' y 'wikipedia_url'."""
    resultado = {"nombre": nombre, "foto_url": None, "wikipedia_url": None}
    try:
        resp = await client.get(
            "https://api.inaturalist.org/v1/taxa",
            params={
                "q": nombre,
                "locale": "es",
                "per_page": 1,
                "rank": "species,genus,family,order",
            },
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

async def buscar_gbif_match(nombre_cientifico: str, client: httpx.AsyncClient) -> dict:
    """Busca coincidencia en GBIF y devuelve el JSON completo."""
    resp = await client.get(
        "https://api.gbif.org/v1/species/match",
        params={"name": nombre_cientifico, "verbose": False},
    )
    resp.raise_for_status()
    return resp.json()