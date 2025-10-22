"""import os
import json
import threading
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DATA_FILE = "data_lab2.json"
LOCK = threading.Lock()

def load_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"books": [], "next_id": 1}, f)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

class BookIn(BaseModel):
    title: str
    author: str
    price: float
    tags: List[str] = []

class BookOut(BookIn):
    id: int

app = FastAPI(title="Lab2 - CRUD Books API")

@app.get("/books", response_model=List[BookOut])
def list_books():
    db = load_db()
    return db["books"]

@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    db = load_db()
    for book in db["books"]:
        if book["id"] == book_id:
            return book
    raise HTTPException(status_code=404, detail="Book not found")

@app.post("/books", response_model=BookOut, status_code=201)
def create_book(book: BookIn):
    with LOCK:
        db = load_db()
        new_id = db.get("next_id", 1)
        record = {"id": new_id, **book.dict()}
        db["books"].append(record)
        db["next_id"] = new_id + 1
        save_db(db)
        return record

@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, book: BookIn):
    with LOCK:
        db = load_db()
        for i, b in enumerate(db["books"]):
            if b["id"] == book_id:
                updated = {"id": book_id, **book.dict()}
                db["books"][i] = updated
                save_db(db)
                return updated
    raise HTTPException(status_code=404, detail="Book not found")

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with LOCK:
        db = load_db()
        for i, b in enumerate(db["books"]):
            if b["id"] == book_id:
                db["books"].pop(i)
                save_db(db)
                return
    raise HTTPException(status_code=404, detail="Book not found")
"""
import os
import json
import threading
from typing import List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATA_FILE = "data_lab2.json"
LOCK = threading.Lock()

# -------------------
# DB helpers
# -------------------
def load_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"books": [], "next_id": 1}, f)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    if "books" not in db:
        db["books"] = []
    if "next_id" not in db:
        db["next_id"] = 1
    return db

def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

# -------------------
# Models
# -------------------
class BookIn(BaseModel):
    title: str
    author: str
    price: float
    tags: List[str] = []

class BookOut(BookIn):
    id: int

# -------------------
# App setup
# -------------------
app = FastAPI(title="Lab4 Books API with Middleware")

# CORS (для тестів з браузера або Postmana)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# -------------------
# Middleware: X-Process-Time
# -------------------
@app.middleware("http")
async def timing_header(request: Request, call_next):
    import time
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000.0
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
    return response

# -------------------
# Middleware: Admin Guard
# -------------------
API_KEY = "my_secret" # можна встановити через середовище
@app.middleware("http")
async def admin_guard(request: Request, call_next):
    if request.url.path.startswith("/admin/"):
        provided = request.headers.get("X-API-Key")
        if provided != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized (missing/invalid X-API-Key)"})
    return await call_next(request)

# -------------------
# Admin endpoint
# -------------------
@app.get("/admin/secret")
def admin_secret():
    return {"ok": True, "msg": "Welcome, admin."}

# -------------------
# CRUD endpoints
# -------------------
@app.get("/books", response_model=List[BookOut])
def list_books():
    db = load_db()
    return db["books"]

@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    db = load_db()
    for book in db["books"]:
        if book["id"] == book_id:
            return book
    return JSONResponse(status_code=404, content={"detail": "Book not found"})

@app.post("/books", response_model=BookOut, status_code=201)
def create_book(book: BookIn):
    with LOCK:
        db = load_db()
        new_id = db.get("next_id", 1)
        record = {"id": new_id, **book.dict()}
        db["books"].append(record)
        db["next_id"] = new_id + 1
        save_db(db)
        return record

@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, book: BookIn):
    with LOCK:
        db = load_db()
        for i, b in enumerate(db["books"]):
            if b["id"] == book_id:
                updated = {"id": book_id, **book.dict()}
                db["books"][i] = updated
                save_db(db)
                return updated
    return JSONResponse(status_code=404, content={"detail": "Book not found"})

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with LOCK:
        db = load_db()
        for i, b in enumerate(db["books"]):
            if b["id"] == book_id:
                db["books"].pop(i)
                save_db(db)
                return
    return JSONResponse(status_code=404, content={"detail": "Book not found"})