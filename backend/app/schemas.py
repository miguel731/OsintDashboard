from pydantic import BaseModel, Field
from typing import List, Optional, Any

class ClientCreate(BaseModel):
    name: str

class ClientOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str
    client_id: Optional[int] = None

class ProjectOut(BaseModel):
    id: int
    name: str
    client_id: Optional[int]
    class Config:
        from_attributes = True

class ScanCreate(BaseModel):
    project_id: int
    target: str
    tools: List[str] = Field(default_factory=list)  # e.g. ["amass","subfinder","theharvester","hibp"]

class ScanOut(BaseModel):
    id: int
    target: str
    status: str
    tools: List[str]
    project_id: int
    class Config:
        from_attributes = True

class FindingOut(BaseModel):
    id: int
    tool: str
    category: str
    value: str
    severity: str
    meta: Any
    class Config:
        from_attributes = True