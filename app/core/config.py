from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    cors_origins: list[str]
    host: str = "0.0.0.0"
    port: int = 8000


def get_settings() -> Settings:
    origins_env = os.getenv(
        "WORK_AGENT_CORS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    )
    return Settings(cors_origins=[o.strip() for o in origins_env.split(",") if o.strip()])
