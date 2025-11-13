import shutil, subprocess
from typing import List, Dict, Any
from .base import OSINTTool

class TheHarvesterTool(OSINTTool):
    id = "theharvester"
    name = "TheHarvester"
    supported_targets = ["domain"]

    def run(self, target: str) -> List[Dict[str, Any]]:
        if not shutil.which("theHarvester"):
            return []
        # Modo texto, parseamos lo básico (emails y hosts encontrados)
        cmd = ["theHarvester", "-d", target, "-b", "all", "-n"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            findings: List[Dict[str, Any]] = []
            for line in p.stdout.splitlines():
                l = line.strip()
                if "@" in l and "." in l:
                    findings.append({"tool": self.id, "category": "email", "value": l, "severity": "info", "meta": {}, "raw": l})
                elif "." in l and " " not in l:
                    findings.append({"tool": self.id, "category": "host", "value": l, "severity": "info", "meta": {}, "raw": l})
            return findings
        except Exception as e:
            return [{"tool": self.id, "category": "error", "value": str(e), "severity": "info", "meta": {}, "raw": None}]