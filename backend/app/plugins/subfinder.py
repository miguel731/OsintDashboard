import shutil, subprocess, json
from typing import List, Dict, Any
from .base import OSINTTool
from ..config import settings
import redis as redislib

r = redislib.from_url(settings.REDIS_URL, decode_responses=True)

class SubfinderTool(OSINTTool):
    id = "subfinder"
    name = "ProjectDiscovery Subfinder"
    supported_targets = ["domain"]

    def run(self, target: str, scan_id: int | None = None) -> List[Dict[str, Any]]:
        if not shutil.which("subfinder"):
            return []
        cmd = ["subfinder", "-d", target, "-json"]
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
                        r.publish(f"scan:{scan_id}:logs", f"[subfinder] {l}")
                    except Exception:
                        pass
                # parseo JSON y push a findings
                try:
                    obj = json.loads(l)
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
                    r.publish(f"scan:{scan_id}:logs", f"[subfinder] error: {e}")
                except Exception:
                    pass
            return [{"tool": self.id, "category": "error", "value": str(e), "severity": "info", "meta": {}, "raw": None}]