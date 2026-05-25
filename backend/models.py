from pydantic import BaseModel
from datetime import date

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