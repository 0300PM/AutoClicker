from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

APP_NAME = "AutoClicker"
APP_VERSION = "1.0.0"
SETTINGS_FILE = "settings.json"


def project_root() -> Path:
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    base = Path(bundle) if bundle else project_root()
    return base / "assets" / name


def config_dir() -> Path:
    override = os.environ.get("AUTOCLICKER_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        roaming = os.environ.get("APPDATA")
        base = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
        return base / APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "autoclicker"


def config_file() -> Path:
    return config_dir() / SETTINGS_FILE


def ensure_dir(path: Path) -> Optional[Path]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        return None
