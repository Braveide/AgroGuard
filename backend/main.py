import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Optional Supabase client
try:
    from supabase import create_client, Client
except Exception:
    Client = None
    create_client = None

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize Supabase if credentials are present
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if SUPABASE_URL and SUPABASE_KEY and create_client:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# FastAPI app
app = FastAPI(title="AgroGuard API")

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from .routers import plagas, imagen, pdf

app.include_router(plagas.router)
app.include_router(imagen.router)
app.include_router(pdf.router)

# Serve frontend static files
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("index.html")

# Initialize DB on startup (if not using Supabase)
@app.on_event("startup")
async def startup_event():
    if supabase is None:
        # Local SQLite DB initialization
        from .services.db_service import init_db
        init_db()

# Export supabase for routers to import
__all__ = ["app", "supabase"]