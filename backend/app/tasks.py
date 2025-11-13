from datetime import datetime
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Scan, Finding
from .plugins import TOOLS_REGISTRY

def save_findings(db: Session, scan: Scan, findings):
    for f in findings:
        db.add(Finding(
            scan_id=scan.id,
            tool=f.get("tool","unknown"),
            category=f.get("category","info"),
            value=f.get("value",""),
            severity=f.get("severity","info"),
            meta=f.get("meta", {}),
            raw=str(f.get("raw",""))[:20000],  # limitado
        ))
    db.commit()

from .celery_app import celery

@celery.task(name="app.tasks.run_scan")
def run_scan(scan_id: int, target: str, tools: list[str]):
    db = SessionLocal()
    try:
        scan = db.query(Scan).get(scan_id)
        if not scan:
            return
        scan.status = "running"
        db.commit()

        all_findings = []
        for tool_id in tools:
            tool = TOOLS_REGISTRY.get(tool_id)
            if not tool:
                continue
            findings = tool.run(target)
            save_findings(db, scan, findings)
            all_findings.extend(findings)

        scan.status = "completed"
        scan.finished_at = datetime.utcnow()
        db.commit()
        return {"count": len(all_findings)}
    except Exception as e:
        scan = db.query(Scan).get(scan_id)
        if scan:
            scan.status = "error"
            db.commit()
        return {"error": str(e)}
    finally:
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