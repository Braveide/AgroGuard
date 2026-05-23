# ---- 1. Imagen base ----
FROM python:3.12-slim-bullseye

# ---- 2. Variables de entorno de Python ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---- 3. Dependencias del sistema ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ---- 4. Copiar requerimientos y instalarlos ----
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- 5. Copiar código de la aplicación ----
COPY . .

# ---- 6. Exponer puerto (FastAPI usa el puerto dinámico de Render) ----
EXPOSE 8000

# ---- 7. Entrypoint – uvicorn adaptado a Render ----
#  CAMBIADO: Ahora lee la variable $PORT que Render le asigna automáticamente en la nube.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]