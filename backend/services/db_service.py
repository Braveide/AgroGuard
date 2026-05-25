import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "agroguard.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bitacora_plagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_plaga TEXT NOT NULL,
            nombre_cientifico TEXT NOT NULL,
            familia TEXT NOT NULL,
            reino TEXT NOT NULL,
            riesgo TEXT NOT NULL,
            ficha_tecnica TEXT NOT NULL,
            fecha TEXT NOT NULL,
            latitud REAL,
            longitud REAL
        )
    """)
    # Ensure latitude and longitude columns exist (for older DBs)
    for col in ["latitud", "longitud"]:
        try:
            cursor.execute(f"ALTER TABLE bitacora_plagas ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()