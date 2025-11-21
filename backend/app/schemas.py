# Módulo: imports + clases Schedule
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

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

class ScheduleCreate(BaseModel):
    project_id: int
    target: str
    tools: List[str] = Field(default_factory=list)
    interval_minutes: int = Field(gt=0)

class ScheduleOut(BaseModel):
    id: int
    project_id: Optional[int]
    target: str
    tools: List[str]
    interval_minutes: int
    enabled: bool
    next_run_at: datetime
    last_run_at: Optional[datetime]
    class Config:
        from_attributes = True