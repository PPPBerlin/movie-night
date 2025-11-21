import os
import sqlite3
import httpx
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Konfiguration
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DB_PATH = "data/movies.db"

# --- Datenbank Setup ---
def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS movies 
                 (id INTEGER PRIMARY KEY, tmdb_id INTEGER, title TEXT, poster_path TEXT, overview TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Hilfsfunktionen ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Routen ---

@app.get("/")
async def home(request: Request):
    conn = get_db_connection()
    movies = conn.execute('SELECT * FROM movies ORDER BY id DESC').fetchall()
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "movies": movies})

@app.get("/api/search")
async def search_tmdb(query: str):
    """Sucht Filme via TMDB API"""
    if not query:
        return []
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&language=de-DE&query={query}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
    
    # Wir geben nur relevante Daten zurueck
    results = []
    for m in data.get('results', [])[:5]: # Top 5 Ergebnisse
        if m.get('poster_path'): # Nur Filme mit Poster
            results.append({
                "tmdb_id": m['id'],
                "title": m['title'],
                "poster_path": f"https://image.tmdb.org/t/p/w500{m['poster_path']}",
                "overview": m['overview']
            })
    return JSONResponse(results)

@app.post("/add")
async def add_movie(tmdb_id: int = Form(...), title: str = Form(...), poster_path: str = Form(...)):
    conn = get_db_connection()
    # Prüfen ob schon da
    exist = conn.execute('SELECT id FROM movies WHERE tmdb_id = ?', (tmdb_id,)).fetchone()
    if not exist:
        conn.execute('INSERT INTO movies (tmdb_id, title, poster_path) VALUES (?, ?, ?)',
                     (tmdb_id, title, poster_path))
        conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete/{movie_id}")
async def delete_movie(movie_id: int):
    conn = get_db_connection()
    conn.execute('DELETE FROM movies WHERE id = ?', (movie_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)
