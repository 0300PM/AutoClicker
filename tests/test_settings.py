import json

import pytest

from click_engine import LEFT, RIGHT
from settings import (
    DEFAULT_VALUES,
    build_settings,
    hotkey_from,
    load,
    parse_int,
    parse_number,
    sanitise,
    save,
    values_with_hotkey,
)


def test_parse_number_accepts_polish_comma_and_spaces():
    assert parse_number("12,5") == 12.5
    assert parse_number(" 7 ") == 7.0
    assert parse_number("8.25") == 8.25
    assert parse_number("wtf", default=3) == 3
    assert parse_number("", default=4) == 4


def test_parse_int_rounds_and_falls_back():
    assert parse_int("12") == 12
    assert parse_int("12,9", 0) == 12
    assert parse_int("none", 5) == 5


def test_defaults_are_valid():
    settings = build_settings(DEFAULT_VALUES)
    assert settings.button == LEFT
    assert settings.cps == 10
    assert settings.total_clicks == 0
    assert settings.position is None


def test_sanitise_clamps_and_fixes_unknown_values():
    cleaned = sanitise({"button": "środkowy", "cps": "9999", "limit": "-4", "jitter": "300", "hotkey_mode": "dziwne"})
    assert cleaned["button"] == LEFT
    assert cleaned["cps"] == "100"
    assert cleaned["limit"] == "0"
    assert cleaned["jitter"] == "90"
    assert cleaned["hotkey_mode"] == "toggle"


def test_build_settings_uses_fixed_position_only_in_fixed_mode():
    values = dict(DEFAULT_VALUES)
    values.update({"position_mode": "fixed", "position_x": "120", "position_y": "60"})
    assert build_settings(values).position == (120, 60)
    values["position_mode"] = "cursor"
    assert build_settings(values).position is None


def test_jitter_zero_disables_randomisation():
    values = dict(DEFAULT_VALUES)
    values.update({"jitter": "0"})
    assert build_settings(values).jitter == 0
    values["jitter"] = "40"
    assert build_settings(values).jitter == pytest.approx(0.4)
    values["jitter"] = "zwykły tekst"
    assert build_settings(values).jitter == 0


def test_hotkey_round_trip_and_missing():
    values = dict(DEFAULT_VALUES)
    binding = hotkey_from(values)
    assert binding is not None and binding.label == "F8"
    assert hotkey_from({"hotkey": None}) is None
    saved = values_with_hotkey(values, None)
    assert saved["hotkey"] is None
    assert hotkey_from(saved) is None


def test_save_and_load_round_trip(tmp_path):
    target = tmp_path / "settings.json"
    values = dict(DEFAULT_VALUES)
    values.update({"button": RIGHT, "cps": "33,5", "limit": "250"})
    assert save(values, target) is True
    stored = json.loads(target.read_text(encoding="utf-8"))
    assert stored["button"] == RIGHT
    loaded = load(target)
    assert loaded["cps"] == "33.5"
    assert loaded["limit"] == "250"


def test_load_tolerates_missing_and_broken_files(tmp_path):
    assert load(tmp_path / "brak.json") == DEFAULT_VALUES
    broken = tmp_path / "psuty.json"
    broken.write_text("{ nie json", encoding="utf-8")
    assert load(broken) == DEFAULT_VALUES
    broken.write_text("[1, 2, 3]", encoding="utf-8")
    assert load(broken) == DEFAULT_VALUES


def test_save_reports_failure_for_unwritable_path(tmp_path):
    blocked = tmp_path / "jest-plikiem"
    blocked.write_text("x", encoding="utf-8")
    assert save(DEFAULT_VALUES, blocked / "settings.json") is False
