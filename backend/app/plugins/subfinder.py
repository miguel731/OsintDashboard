import shutil, subprocess, json
from typing import List, Dict, Any
from .base import OSINTTool

class SubfinderTool(OSINTTool):
    id = "subfinder"
    name = "ProjectDiscovery Subfinder"
    supported_targets = ["domain"]

    def run(self, target: str) -> List[Dict[str, Any]]:
        if not shutil.which("subfinder"):
            return []
        cmd = ["subfinder", "-d", target, "-json"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            findings: List[Dict[str, Any]] = []
            for line in p.stdout.splitlines():
                try:
                    obj = json.loads(line)
                    host = obj.get("host") or obj.get("data")
                    if host:
                        findings.append({
                            "tool": self.id,
                            "category": "subdomain",
                            "value": host,
                            "severity": "info",
                            "meta": obj,
                            "raw": obj,
                        })
                except json.JSONDecodeError:
                    continue
            return findings
        except Exception as e:
            return [{"tool": self.id, "category": "error", "value": str(e), "severity": "info", "meta": {}, "raw": None}]