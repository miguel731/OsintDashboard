from typing import List, Dict, Any
import httpx
from .base import OSINTTool
from ..config import settings

class SpiderfootTool(OSINTTool):
    id = "spiderfoot"
    name = "Spiderfoot"
    supported_targets = ["domain", "ip"]

    def run(self, target: str) -> List[Dict[str, Any]]:
        base = settings.SPIDERFOOT_URL.strip()
        if not base:
            return []
        try:
            # Nota: la API y autenticación de Spiderfoot varían por despliegue.
            # Este stub intenta un endpoint genérico; ajustaremos cuando definamos la imagen/API.
            url = f"{base}/api/query?target={target}"
            r = httpx.get(url, timeout=30)
            if r.status_code != 200:
                return [{"tool": self.id, "category": "error", "value": f"HTTP {r.status_code}", "severity": "info", "meta": {}, "raw": r.text}]
            data = r.json()
            findings: List[Dict[str, Any]] = []
            for item in data.get("results", []):
                findings.append({
                    "tool": self.id,
                    "category": item.get("category", "info"),
                    "value": item.get("value", ""),
                    "severity": item.get("severity", "info"),
                    "meta": item,
                    "raw": item
                })
            return findings
        except Exception as e:
            return [{"tool": self.id, "category": "error", "value": str(e), "severity": "info", "meta": {}, "raw": None}]