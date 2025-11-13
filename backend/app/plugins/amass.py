import shutil, subprocess, json
from typing import List, Dict, Any
from .base import OSINTTool

class AmassTool(OSINTTool):
    id = "amass"
    name = "OWASP Amass"
    supported_targets = ["domain"]

    def run(self, target: str) -> List[Dict[str, Any]]:
        if not shutil.which("amass"):
            return []
        cmd = ["amass", "enum", "-d", target, "-json", "-"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            findings: List[Dict[str, Any]] = []
            for line in p.stdout.splitlines():
                try:
                    obj = json.loads(line)
                    name = obj.get("name")
                    if name:
                        findings.append({
                            "tool": self.id,
                            "category": "subdomain",
                            "value": name,
                            "severity": "info",
                            "meta": {"sources": obj.get("sources", []), "addresses": obj.get("addresses", [])},
                            "raw": obj,
                        })
                except json.JSONDecodeError:
                    continue
            return findings
        except Exception as e:
            return [{"tool": self.id, "category": "error", "value": str(e), "severity": "info", "meta": {}, "raw": None}]