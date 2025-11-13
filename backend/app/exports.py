import csv
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session
from .models import Scan, Finding

def export_csv(db: Session, scan_id: int) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["tool","category","value","severity","meta"])
    for f in db.query(Finding).filter(Finding.scan_id==scan_id).all():
        writer.writerow([f.tool, f.category, f.value, f.severity, f.meta])
    return output.getvalue().encode("utf-8")

def export_pdf(db: Session, scan_id: int) -> bytes:
    scan = db.query(Scan).get(scan_id)
    findings = db.query(Finding).filter(Finding.scan_id==scan_id).all()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Reporte OSINT Scan #{scan_id}")
    c.drawString(40, 800, f"Scan #{scan_id} - Target: {scan.target} - Status: {scan.status}")
    c.drawString(40, 780, f"Herramientas: {', '.join(scan.tools)}")
    y = 760
    for f in findings[:40]:  # limitar para demo
        c.drawString(40, y, f"[{f.tool}] {f.category}: {f.value}")
        y -= 16
        if y < 60:
            c.showPage()
            y = 800
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf