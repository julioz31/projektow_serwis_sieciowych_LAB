import os
import json
import threading
import time as _time
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from fastapi_pagination import Page, paginate, add_pagination

DATA_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")
LOCK = threading.Lock()

def _ensure_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": [], "next_id": 1}, f, ensure_ascii=False, indent=2)

def load_db():
    _ensure_db()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    done: bool = False
    priority: int = 1
    labels: List[str] = []
    due_date: Optional[str] = None  # ISO date format

class TaskOut(TaskIn):
    id: int
    created_at: str

app = FastAPI(
    title="LAB03 - Tasks API (API Key + Pagination)",
    description="CRUD задач + X-API-Key + пагінація (limit/offset), q, sort asc/desc по created_at.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#Middleware dla czasu
@app.middleware("http")
async def timing_header(request: Request, call_next):
    start = _time.perf_counter()
    resp = await call_next(request)
    dur_ms = (_time.perf_counter() - start) * 1000.0
    resp.headers["X-Process-Time"] = f"{dur_ms:.2f}ms"
    return resp

#X-API-Key
API_KEY = "secret"

@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    if request.url.path.startswith("/tasks"):
        provided = request.headers.get("X-API-Key")
        if provided != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized (X-API-Key)"})
    return await call_next(request)

@app.get("/health")
def health():
    return {"status": "ok"}

# Lista z filtrem, sortowaniem, paginacją
@app.get("/tasks", response_model=Page[TaskOut])
def list_tasks(q: Optional[str] = None, sort: str = "desc"):
    db = load_db()
    data = db["tasks"]

    if q:
        ql = q.lower()
        data = [t for t in data if ql in t["title"].lower() or any(ql in l.lower() for l in t.get("labels", []))]

    data = sorted(data, key=lambda t: t["created_at"], reverse=(sort == "desc"))
    return paginate(data)

# CRUD
@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(task: TaskIn):
    with LOCK:
        db = load_db()
        new_id = int(db["next_id"])
        record = {
            "id": new_id,
            "created_at": datetime.utcnow().isoformat(),
            **task.dict()
        }
        db["tasks"].append(record)
        db["next_id"] = new_id + 1
        save_db(db)
        return record

@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int):
    db = load_db()
    for t in db["tasks"]:
        if t["id"] == task_id:
            return t
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task: TaskIn):
    with LOCK:
        db = load_db()
        for i, t in enumerate(db["tasks"]):
            if t["id"] == task_id:
                updated = {"id": task_id, "created_at": t["created_at"], **task.dict()}
                db["tasks"][i] = updated
                save_db(db)
                return updated
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with LOCK:
        db = load_db()
        for i, t in enumerate(db["tasks"]):
            if t["id"] == task_id:
                db["tasks"].pop(i)
                save_db(db)
                return
    raise HTTPException(status_code=404, detail="Task not found")

add_pagination(app)