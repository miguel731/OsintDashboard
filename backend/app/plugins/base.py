from typing import Dict, List, Any

class OSINTTool:
    id: str
    name: str
    supported_targets: List[str]  # ["domain","ip","email"]

    def run(self, target: str, scan_id: int | None = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

TOOLS_REGISTRY: Dict[str, OSINTTool] = {}

def register_tool(tool: OSINTTool):
    TOOLS_REGISTRY[tool.id] = tool


from typing import Dict, List, Any

class OSINTTool:
    id: str
    name: str
    supported_targets: List[str]  # ["domain","ip","email"]

    def run(self, target: str, scan_id: int | None = None) -> List[Dict[str, Any]]:
        raise NotImplementedError

TOOLS_REGISTRY: Dict[str, OSINTTool] = {}

def register_tool(tool: OSINTTool):
    TOOLS_REGISTRY[tool.id] = tool