from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..core.config import Settings, _settings_file_path, get_settings
from ..models.settings import AppSettings, AppSettingsUpdate


def _settings_to_dict(settings: Settings) -> dict[str, Any]:
    data = asdict(settings)
    data["frame_storage_dir"] = str(settings.frame_storage_dir)
    return data


def current_settings() -> AppSettings:
    return AppSettings(**_settings_to_dict(get_settings()))


def save_settings(update: AppSettingsUpdate) -> AppSettings:
    current = _settings_to_dict(get_settings())
    patch = update.model_dump(exclude_unset=True, by_alias=False)
    for key, value in patch.items():
        if value is not None:
            current[key] = value

    path: Path = _settings_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current_settings()