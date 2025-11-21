from .base import TOOLS_REGISTRY, register_tool
from .subfinder import SubfinderTool
from .theharvester import TheHarvesterTool

# Registrar herramientas disponibles (puedes comentar las que no uses)
register_tool(SubfinderTool())
register_tool(TheHarvesterTool())