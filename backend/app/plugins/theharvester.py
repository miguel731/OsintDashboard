import shutil, subprocess
from typing import List, Dict, Any
from .base import OSINTTool
from ..config import settings
import redis as redislib

r = redislib.from_url(settings.REDIS_URL, decode_responses=True)

class TheHarvesterTool(OSINTTool):
    id = "theharvester"
    name = "TheHarvester"
    supported_targets = ["domain"]

    def run(self, target: str, scan_id: int | None = None) -> List[Dict[str, Any]]:
        if not shutil.which("theHarvester"):
            return []
        cmd = ["theHarvester", "-d", target, "-b", "all", "-n"]
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            findings: List[Dict[str, Any]] = []
            while True:
                line = p.stdout.readline()
                if not line:
                    break
                l = line.strip()
                if scan_id:
                    try:
                        r.publish(f"scan:{scan_id}:logs", f"[theharvester] {l}")
                    except Exception:
                        pass
                # parseo de emails/hosts y push a findings
                if "@" in l and "." in l:
                    findings.append({"tool": self.id, "category": "email", "value": l, "severity": "info", "meta": {}, "raw": l})
                elif "." in l and " " not in l:
                    findings.append({"tool": self.id, "category": "host", "value": l, "severity": "info", "meta": {}, "raw": l})
                if scan_id and r.get(f"scan:{scan_id}:stop") == "1":
                    try:
                        p.terminate()
                    except Exception:
                        pass
                    break
            try:
                p.wait(timeout=5)
            except Exception:
                pass
            return findings
        except Exception as e:
            if scan_id:
                try:
                    r.publish(f"scan:{scan_id}:logs", f"[theharvester] error: {e}")
                except Exception:
                    pass
            return [{"tool": self.id, "category": "error", "value": str(e), "severity": "info", "meta": {}, "raw": None}]