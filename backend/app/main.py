from fastapi import FastAPI, Depends, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from .db import Base, engine, get_db
from .models import Client, Project, Scan, Finding
from .schemas import ClientCreate, ClientOut, ProjectCreate, ProjectOut, ScanCreate, ScanOut, FindingOut
from .tasks import run_scan
from .exports import export_csv, export_pdf
from .celery_app import celery
from .config import settings
import redis as redislib
from datetime import datetime
from fastapi import WebSocket
import asyncio

app = FastAPI(title="OSINT Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

r = redislib.from_url(settings.REDIS_URL, decode_responses=True)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

# Clientes
@app.post("/api/clients", response_model=ClientOut)
def create_client(body: ClientCreate, db: Session = Depends(get_db)):
    c = Client(name=body.name)
    db.add(c); db.commit(); db.refresh(c)
    return c

@app.get("/api/clients", response_model=List[ClientOut])
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()

# Proyectos
@app.post("/api/projects", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(name=body.name, client_id=body.client_id)
    db.add(p); db.commit(); db.refresh(p)
    return p

@app.get("/api/projects", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).get(project_id)
    if not p: raise HTTPException(404, "Proyecto no encontrado")
    for s in db.query(Scan).filter(Scan.project_id==project_id).all():
        db.delete(s)
    db.delete(p)
    db.commit()
    return {"ok": True}

# Scans
@app.post("/api/scans", response_model=ScanOut)
def create_scan(body: ScanCreate, db: Session = Depends(get_db)):
    s = Scan(project_id=body.project_id, target=body.target, tools=body.tools, status="pending")
    db.add(s); db.commit(); db.refresh(s)
    async_res = run_scan.delay(s.id, body.target, body.tools)
    try:
        r.set(f"scan:{s.id}:task", async_res.id)
        s.status = "queued"
        db.commit(); db.refresh(s)
    except Exception:
        pass
    return s

@app.get("/api/scans", response_model=List[ScanOut])
def list_scans(db: Session = Depends(get_db)):
    return db.query(Scan).order_by(Scan.id.desc()).all()

@app.get("/api/scans/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    s = db.query(Scan).get(scan_id)
    if not s: raise HTTPException(404, "Scan no encontrado")
    return s


@app.get("/api/scans/{scan_id}/findings", response_model=List[FindingOut])
def get_findings(scan_id: int, db: Session = Depends(get_db)):
    return db.query(Finding).filter(Finding.scan_id==scan_id).all()

@app.post("/api/scans/{scan_id}/start", response_model=ScanOut)
def start_scan(scan_id: int, db: Session = Depends(get_db)):
    s = db.query(Scan).get(scan_id)
    if not s: raise HTTPException(404, "Scan no encontrado")
    if s.status in ("running", "queued"):
        raise HTTPException(400, "El scan ya está en curso")
    async_res = run_scan.delay(s.id, s.target, s.tools)
    r.set(f"scan:{s.id}:task", async_res.id)
    s.status = "queued"
    db.commit(); db.refresh(s)
    return s

@app.post("/api/scans/{scan_id}/stop", response_model=ScanOut)
def stop_scan(scan_id: int, db: Session = Depends(get_db)):
    s = db.query(Scan).get(scan_id)
    if not s: raise HTTPException(404, "Scan no encontrado")

    try:
        r.set(f"scan:{s.id}:stop", "1", ex=3600)
    except Exception:
        pass

    task_id = r.get(f"scan:{s.id}:task")
    if not task_id:
        try:
            i = celery.control.inspect()
            active = i.active() or {}
            reserved = i.reserved() or {}
            def find_task_id(buckets):
                for _, tasks in buckets.items():
                    for t in tasks:
                        if t.get("name") == "app.tasks.run_scan":
                            args = str(t.get("args"))
                            if f"({scan_id}," in args or f"{scan_id}" in args:
                                return t.get("id")
                return None
            task_id = find_task_id(active) or find_task_id(reserved)
        except Exception:
            task_id = None

    try:
        if task_id:
            celery.control.revoke(task_id, terminate=True, signal="SIGTERM")
            r.delete(f"scan:{s.id}:task")
    except Exception:
        pass

    s.status = "stopped"
    s.finished_at = datetime.utcnow()
    db.commit(); db.refresh(s)
    return s

@app.websocket("/ws/scans/{scan_id}/logs")
async def ws_scan_logs(websocket: WebSocket, scan_id: int):
    await websocket.accept()
    pubsub = r.pubsub()
    pubsub.subscribe(f"scan:{scan_id}:logs")
    try:
        while True:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                await websocket.send_text(str(msg.get("data")))
            await asyncio.sleep(0.2)
    except Exception:
        pass
    finally:
        try:
            pubsub.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except RuntimeError:
            pass
        except Exception:
            pass

# Exportaciones
from fastapi.responses import StreamingResponse

@app.get("/api/exports/{scan_id}.csv")
def export_scan_csv(scan_id: int, db: Session = Depends(get_db)):
    data = export_csv(db, scan_id)
    return StreamingResponse(io.BytesIO(data), media_type="text/csv", headers={
        "Content-Disposition": f'attachment; filename="scan_{scan_id}.csv"'
    })

import io
@app.get("/api/exports/{scan_id}.pdf")
def export_scan_pdf(scan_id: int, db: Session = Depends(get_db)):
    data = export_pdf(db, scan_id)
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="scan_{scan_id}.pdf"'
    })
@app.delete("/api/scans/{scan_id}", status_code=204)
def delete_scan(scan_id: int, db: Session = Depends(get_db)):
    s = db.query(Scan).get(scan_id)
    if not s:
        raise HTTPException(404, "Scan no encontrado")
    try:
        r.setex(f"scan:{scan_id}:stop", 600, "1")
    except Exception:
        pass
    try:
        task_id = r.get(f"scan:{scan_id}:task")
        if task_id:
            try:
                celery.control.revoke(task_id, terminate=True, signal="SIGTERM")
            except Exception:
                pass
            try:
                r.delete(f"scan:{scan_id}:task")
            except Exception:
                pass
    except Exception:
        pass
    db.delete(s)
    db.commit()
    return None