from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _settings_file_path() -> Path:
    return Path(_env("WORK_AGENT_SETTINGS_FILE", "./data/settings.json"))


def _load_persisted_settings() -> dict:
    path = _settings_file_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _apply_persisted(base: dict, persisted: dict) -> dict:
    for key in base:
        if key not in persisted or persisted[key] is None:
            continue
        if key == "frame_storage_dir":
            base[key] = Path(str(persisted[key]))
        else:
            base[key] = persisted[key]
    return base


@dataclass
class Settings:
    cors_origins: list[str] = field(default_factory=list)
    host: str = "0.0.0.0"
    port: int = 8000

    # providers
    frame_provider: str = "mock"            # mock | obs | file
    hid_bridge: str = "mock"                # mock | esp32_http | esp32_ws

    # OBS
    obs_ws_url: str = "ws://localhost:4455"
    obs_ws_password: str = ""
    obs_source_name: str = "VDI Capture"

    # ESP32
    esp32_base_url: str = "http://192.168.31.234"
    esp32_ws_url: str = "ws://192.168.31.234:81/hid"
    esp32_api_token: str = "change-me"

    # VDI resolution
    vdi_width: int = 1920
    vdi_height: int = 1080

    # timings (ms)
    frame_refresh_interval_ms: int = 1000
    after_action_refresh_delay_ms: int = 500
    stale_frame_warning_ms: int = 5000
    stale_frame_block_ms: int = 15000
    hid_command_timeout_ms: int = 5000

    # storage
    frame_storage_dir: Path = Path("./data/frames")


def get_settings() -> Settings:
    origins_env = _env(
        "WORK_AGENT_CORS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    )
    values = {
        "cors_origins": [o.strip() for o in origins_env.split(",") if o.strip()],
        "frame_provider": _env("FRAME_PROVIDER", "mock"),
        "hid_bridge": _env("HID_BRIDGE", "mock"),
        "obs_ws_url": _env("OBS_WS_URL", "ws://localhost:4455"),
        "obs_ws_password": _env("OBS_WS_PASSWORD", ""),
        "obs_source_name": _env("OBS_SOURCE_NAME", "VDI Capture"),
        "esp32_base_url": _env("ESP32_BASE_URL", "http://192.168.31.234"),
        "esp32_ws_url": _env("ESP32_WS_URL", "ws://192.168.31.234:81/hid"),
        "esp32_api_token": _env("ESP32_API_TOKEN", "change-me"),
        "vdi_width": _env_int("VDI_WIDTH", 1920),
        "vdi_height": _env_int("VDI_HEIGHT", 1080),
        "frame_refresh_interval_ms": _env_int("FRAME_REFRESH_INTERVAL_MS", 1000),
        "after_action_refresh_delay_ms": _env_int("AFTER_ACTION_REFRESH_DELAY_MS", 500),
        "stale_frame_warning_ms": _env_int("STALE_FRAME_WARNING_MS", 5000),
        "stale_frame_block_ms": _env_int("STALE_FRAME_BLOCK_MS", 15000),
        "hid_command_timeout_ms": _env_int("HID_COMMAND_TIMEOUT_MS", 5000),
        "frame_storage_dir": Path(_env("FRAME_STORAGE_DIR", "./data/frames")),
    }
    return Settings(**_apply_persisted(values, _load_persisted_settings()))
