import httpx
from typing import List, Dict, Any
from .base import OSINTTool
from ..config import settings

class HIBPTool(OSINTTool):
    id = "hibp"
    name = "Have I Been Pwned"
    supported_targets = ["email"]

    def run(self, target: str) -> List[Dict[str, Any]]:
        # Solo emails. Si no lo es, retorna sin hallazgos.
        if "@" not in target:
            return []
        api_key = settings.HIBP_API_KEY
        headers = {
            "hibp-api-key": api_key,
            "User-Agent": "osint-dashboard",
        }
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{target}"
        try:
            r = httpx.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                breaches = r.json()
                findings = []
                for b in breaches:
                    findings.append({
                        "tool": self.id,
                        "category": "leak",
                        "value": b.get("Name", "Unknown"),
                        "severity": "high",
                        "meta": {
                            "domain": b.get("Domain"),
                            "breachDate": b.get("BreachDate"),
                            "pwnCount": b.get("PwnCount"),
                            "dataClasses": b.get("DataClasses", []),
                        },
                        "raw": b,
                    })
                return findings
            elif r.status_code == 404:
                return []
            else:
                return [{"tool": self.id, "category": "error", "value": f"HTTP {r.status_code}", "severity": "info", "meta": {}, "raw": r.text}]
        except Exception as e:
            return [{"tool": self.id, "category": "error", "value": str(e), "severity": "info", "meta": {}, "raw": None}]