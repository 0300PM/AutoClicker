from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from click_engine import BOTH, LEFT, MAX_CPS, MIN_CPS, RIGHT, ClickSettings, clamp_cps, clamp_jitter
from hotkeys import KeyBinding
from paths import config_file, ensure_dir

DEFAULT_VALUES: Dict[str, Any] = {
    "button": LEFT,
    "cps": "10",
    "double_click": False,
    "jitter": 15,
    "limit": "0",
    "position_mode": "cursor",
    "position_x": "0",
    "position_y": "0",
    "restore_cursor": False,
    "hotkey": {"label": "F8", "name": "f8", "char": None, "vk": 119, "keysym": "F8"},
    "hotkey_mode": "toggle",
}

BUTTON_VALUES = {LEFT, RIGHT, BOTH}
POSITION_MODES = {"cursor", "fixed"}
HOTKEY_MODES = {"toggle", "hold"}


def parse_number(text: str, default: float = 0.0) -> float:
    cleaned = str(text).strip().replace(" ", "").replace(",", ".")
    if not cleaned:
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def parse_int(text: str, default: int = 0) -> int:
    cleaned = str(text).strip().replace(" ", "").replace(",", ".")
    if not cleaned:
        return default
    try:
        return int(float(cleaned))
    except ValueError:
        return default


def sanitise(values: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(DEFAULT_VALUES)
    merged.update({key: value for key, value in values.items() if key in DEFAULT_VALUES})
    if merged["button"] not in BUTTON_VALUES:
        merged["button"] = LEFT
    if merged["position_mode"] not in POSITION_MODES:
        merged["position_mode"] = "cursor"
    if merged["hotkey_mode"] not in HOTKEY_MODES:
        merged["hotkey_mode"] = "toggle"
    merged["cps"] = f"{clamp_cps(parse_number(merged['cps'], 10.0)):g}"
    merged["jitter"] = str(int(clamp_jitter(parse_number(merged["jitter"], 0.0) / 100.0) * 100))
    merged["limit"] = str(max(0, parse_int(merged["limit"], 0)))
    merged["position_x"] = str(parse_int(merged["position_x"], 0))
    merged["position_y"] = str(parse_int(merged["position_y"], 0))
    for key in ("double_click", "restore_cursor"):
        merged[key] = bool(merged[key])
    return merged


def load(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or config_file()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULT_VALUES)
    if not isinstance(raw, dict):
        return dict(DEFAULT_VALUES)
    return sanitise(raw)


def save(values: Dict[str, Any], path: Optional[Path] = None) -> bool:
    target = path or config_file()
    payload = json.dumps(sanitise(values), ensure_ascii=False, indent=2)
    try:
        if ensure_dir(target.parent) is None:
            return False
        target.write_text(payload, encoding="utf-8")
    except OSError:
        return False
    return True


def build_settings(values: Dict[str, Any]) -> ClickSettings:
    position: Optional[Tuple[int, int]] = None
    if values.get("position_mode") == "fixed":
        position = (parse_int(values.get("position_x", "0")), parse_int(values.get("position_y", "0")))
    jitter = parse_number(values.get("jitter", 0), 0.0) / 100.0
    return ClickSettings(
        button=values.get("button", LEFT),
        cps=clamp_cps(parse_number(values.get("cps", "10"), 10.0)),
        double_click=bool(values.get("double_click")),
        jitter=clamp_jitter(jitter),
        total_clicks=max(0, parse_int(values.get("limit", "0"), 0)),
        position=position,
        restore_cursor=bool(values.get("restore_cursor")),
    )


def hotkey_from(values: Dict[str, Any]) -> Optional[KeyBinding]:
    return KeyBinding.from_dict(values.get("hotkey"))


def values_with_hotkey(values: Dict[str, Any], binding: Optional[KeyBinding]) -> Dict[str, Any]:
    updated = dict(values)
    updated["hotkey"] = binding.as_dict() if binding is not None else None
    return updated


__all__ = [
    "DEFAULT_VALUES",
    "MAX_CPS",
    "MIN_CPS",
    "build_settings",
    "hotkey_from",
    "load",
    "parse_int",
    "parse_number",
    "sanitise",
    "save",
    "values_with_hotkey",
]
