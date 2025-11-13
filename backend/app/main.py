from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from .db import Base, engine, get_db
from .models import Client, Project, Scan, Finding
from .schemas import ClientCreate, ClientOut, ProjectCreate, ProjectOut, ScanCreate, ScanOut, FindingOut
from .tasks import run_scan
from .exports import export_csv, export_pdf

app = FastAPI(title="OSINT Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

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

# Scans
@app.post("/api/scans", response_model=ScanOut)
def create_scan(body: ScanCreate, db: Session = Depends(get_db)):
    s = Scan(project_id=body.project_id, target=body.target, tools=body.tools, status="pending")
    db.add(s); db.commit(); db.refresh(s)
    run_scan.delay(s.id, body.target, body.tools)
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