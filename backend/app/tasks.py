# Módulo: imports y cliente Redis
from datetime import datetime
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Scan, Finding
from .plugins import TOOLS_REGISTRY
import json
import redis as redislib
from .celery_app import celery
from .config import settings

r = redislib.from_url(settings.REDIS_URL, decode_responses=True)

# Task principal: usa r inicializado y save_findings
@celery.task(name="app.tasks.run_scan")
def run_scan(scan_id: int, target: str, tools: list[str]):
    db = SessionLocal()
    try:
        scan = db.query(Scan).get(scan_id)
        if not scan:
            return
        try:
            r.set(f"scan:{scan_id}:task", run_scan.request.id)
        except Exception:
            pass

        scan.status = "running"
        db.commit()

        all_findings = []
        for tool_id in tools:
            if r.get(f"scan:{scan_id}:stop") == "1":
                scan.status = "stopped"
                scan.finished_at = datetime.utcnow()
                db.commit()
                break

            tool = TOOLS_REGISTRY.get(tool_id)
            if not tool:
                continue

            try:
                r.publish(f"scan:{scan_id}:logs", f"== Ejecutando {tool.name} ==")
            except Exception:
                pass

            findings = tool.run(target, scan_id)
            save_findings(db, scan, findings)
            all_findings.extend(findings)

        if scan.status != "stopped":
            scan.status = "completed"
            scan.finished_at = datetime.utcnow()
            db.commit()
            try:
                r.publish(f"scan:{scan_id}:logs", f"== Escaneo finalizado. Hallazgos: {len(all_findings)} ==")
            except Exception:
                pass

        return {"count": len(all_findings)}
    except Exception as e:
        scan = db.query(Scan).get(scan_id)
        if scan:
            scan.status = "error"
            db.commit()
        try:
            r.publish(f"scan:{scan_id}:logs", f"ERROR: {e}")
        except Exception:
            pass
        return {"error": str(e)}
    finally:
        try:
            r.delete(f"scan:{scan_id}:task")
        except Exception:
            pass
        db.close()

@celery.task(name="app.tasks.run_scheduled_scan")
def run_scheduled_scan(target: str, tools: list[str]):
    # Puede crear un scan "programado" sin proyecto, o con uno por defecto
    db = SessionLocal()
    try:
        scan = Scan(target=target, status="pending", tools=tools, project_id=None)
        db.add(scan)
        db.commit()
        run_scan.delay(scan.id, target, tools)
        return {"scan_id": scan.id}
    finally:
        db.close()

# Función utilitaria para persistir hallazgos
def save_findings(db: Session, scan: Scan, findings: list[dict]) -> None:
    if not findings:
        return
    objs = []
    for item in findings:
        objs.append(Finding(
            scan_id=scan.id,
            tool=item.get("tool", "unknown"),
            category=item.get("category", "info"),
            value=str(item.get("value", "")),
            severity=item.get("severity", "info"),
            meta=item.get("meta", {}),
            raw=(json.dumps(item["raw"]) if item.get("raw") is not None else None),
        ))
    db.add_all(objs)
    db.commit()