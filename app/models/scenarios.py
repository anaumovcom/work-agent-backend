from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Scenario(BaseModel):
    id: str
    name: str
    description: str
    trigger: str
    steps: int
    last_run: str
    success_rate: float
    enabled: bool


class ScenarioPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger: Optional[str] = None
    enabled: Optional[bool] = None
