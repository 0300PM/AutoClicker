import os
import sys
import time
from types import SimpleNamespace

import pytest
from conftest import FakeMouse

from hotkeys import KeyBinding


def display_available() -> bool:
    if sys.platform.startswith(("win", "darwin")):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


pytestmark = pytest.mark.skipif(not display_available(), reason="potrzebny serwer X / Wayland")


def pynput_key(name=None, char=None, vk=0):
    return SimpleNamespace(name=name, char=char, vk=vk)


def tk_event(keysym, char="", keycode=0):
    return SimpleNamespace(keysym=keysym, char=char, keycode=keycode)


def pump(app, seconds=0.3):
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        app.update()
        time.sleep(0.01)
    app.update()


def log_text(app):
    return app._log.get("1.0", "end")


@pytest.fixture
def gui(tmp_path):
    from app import AutoClickerApp

    mouse = FakeMouse()
    app = AutoClickerApp(mouse=mouse, config_path=tmp_path / "settings.json")
    yield app, mouse
    app._on_close()


def test_widgets_start_with_defaults(gui):
    app, _ = gui
    assert app._cps.get() == "10"
    assert app._button.get() == "left"
    assert app._hotkey_label.get() == "F8"
    assert app._status.cget("text") == "●  GOTOWY"
    assert not app.running


def test_start_button_clicks_and_updates_status(gui):
    app, mouse = gui
    app._cps.set("40")
    app.start()
    pump(app, 0.3)
    assert app.running
    assert len(mouse.press_log) > 5
    assert app._status.cget("text") == "●  KLIKAM"
    assert int(app._stat_clicks.cget("text")) > 5
    app.stop()
    pump(app, 0.25)
    assert not app.running
    assert app._status.cget("text") == "●  GOTOWY"
    assert "Wykonano" in log_text(app)
    assert app._result is not None and app._result.error is None


def test_right_button_choice(gui):
    app, mouse = gui
    app._button.set("right")
    app._cps.set("60")
    app._limit.set("6")
    app.start()
    pump(app, 0.6)
    assert set(mouse.press_log) == {"right"}
    assert not app.running


def test_limit_stops_engine_without_manual_stop(gui):
    app, mouse = gui
    app._cps.set("60")
    app._limit.set("10")
    app.start()
    pump(app, 1.0)
    assert len(mouse.press_log) == 10
    assert app.engine is None
    assert "pozostało" not in log_text(app)


def test_position_is_taken_from_cursor(gui):
    app, _ = gui
    app.mouse = FakeMouse(position=(321, 654))
    app._grab_cursor_position()
    assert (app._pos_x.get(), app._pos_y.get()) == ("321", "654")
    assert app._position_mode.get() == "fixed"
    settings = app.validated_settings()
    assert settings.position == (321, 654)


def test_negative_coordinates_are_rejected(gui):
    app, _ = gui
    app._position_mode.set("fixed")
    app._pos_x.set("-5")
    assert app.validated_settings() is None
    assert "ujemne" in log_text(app)


def test_jitter_stepper_clamps_to_range(gui):
    app, _ = gui
    app._bump_jitter(500)
    assert app._jitter_text.get() == "90"
    app._normalise_jitter()
    assert app.validated_settings().jitter == 0.9
    app._jitter_text.set("-20")
    app._normalise_jitter()
    assert app._jitter_text.get() == "0"
    assert app.validated_settings().jitter == 0


def test_garbage_cps_is_clamped_to_range(gui):
    app, _ = gui
    app._cps.set("bzdura")
    settings = app.validated_settings()
    assert settings.cps == 10
    assert app._cps.get() == "10"
    app._cps.set("99999")
    assert app.validated_settings().cps == 100


def test_toggle_hotkey_starts_and_stops(gui):
    app, mouse = gui
    app._handle_hook_key(pynput_key(name="f8", vk=119), True)
    pump(app, 0.2)
    assert app.running
    app._handle_hook_key(pynput_key(name="f8", vk=119), False)
    time.sleep(0.08)
    app._handle_hook_key(pynput_key(name="f8", vk=119), True)
    pump(app, 0.2)
    assert not app.running
    clicks = len(mouse.press_log)
    app._handle_hook_key(pynput_key(name="f8", vk=119), False)
    time.sleep(0.08)
    app._handle_hook_key(pynput_key(name="f8", vk=119), True)
    pump(app, 0.2)
    assert app.running
    assert len(mouse.press_log) > clicks
    app._handle_hook_key(pynput_key(name="f8", vk=119), False)


def test_key_auto_repeat_does_not_toggle_repeatedly(gui):
    app, _ = gui
    for _ in range(5):
        app._handle_hook_key(pynput_key(name="f8", vk=119), True)
        time.sleep(0.06)
    pump(app, 0.15)
    assert app.running


def test_hold_mode_clicks_only_while_key_is_down(gui):
    app, mouse = gui
    app._mode.set("hold")
    app._cps.set("50")
    app._handle_hook_key(pynput_key(name="f8", vk=119), True)
    pump(app, 0.25)
    assert app.running
    pressed = len(mouse.press_log)
    app._handle_hook_key(pynput_key(name="f8", vk=119), False)
    pump(app, 0.2)
    assert not app.running
    time.sleep(0.2)
    assert len(mouse.press_log) == pressed


def test_emergency_key_stops_clicking(gui):
    app, _ = gui
    app.start()
    pump(app, 0.15)
    assert app.running
    app._handle_hook_key(pynput_key(name="f10", vk=121), True)
    pump(app, 0.2)
    assert not app.running
    assert "Awaryjny stop" in log_text(app)


def test_local_keybinding_handler(gui):
    app, _ = gui
    assert "<KeyPress-F8>" in app._local_sequences
    assert app._on_window_press(tk_event("F8", "", 119)) == "break"
    pump(app, 0.15)
    assert app.running
    assert app._on_window_press(tk_event("x", "x", 88)) is None


def test_hotkey_is_ignored_while_typing_in_field(gui):
    app, _ = gui
    app._cps_entry.focus_force()
    app.update()
    assert app.focus_get() is app._cps_entry
    assert app._on_window_press(tk_event("F8", "", 119)) is None
    pump(app, 0.1)
    assert not app.running


def test_assigning_new_hotkey_rebinds_and_saves(gui, tmp_path):
    app, _ = gui
    app._apply_hotkey(KeyBinding.from_event(tk_event("F7", "", 118)))
    assert app._hotkey_label.get() == "F7"
    assert "<KeyPress-F7>" in app._local_sequences
    assert "<KeyPress-F8>" not in app._local_sequences
    pump(app, 0.6)
    assert app.running is False
    app._handle_hook_key(pynput_key(name="f7", vk=118), True)
    pump(app, 0.15)
    assert app.running
    app.stop()
    pump(app, 0.1)
    saved = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert '"F7"' in saved


def test_modifier_cannot_be_assigned(gui):
    app, _ = gui
    binding = KeyBinding.from_event(tk_event("Control_L", "", 162))
    assert binding.is_modifier


def test_clearing_hotkey_shows_placeholder(gui):
    app, _ = gui
    app._clear_hotkey()
    assert app._hotkey_label.get() == "nie ustawiony"
    assert app._hotkey is None
    pump(app, 0.6)
    assert app._local_sequences and all("KeyPress-F10" in seq for seq in app._local_sequences)
    app._handle_hook_key(pynput_key(name="f8", vk=119), True)
    pump(app, 0.15)
    assert not app.running


def test_reset_defaults_restores_f8_and_cps(gui):
    app, _ = gui
    app._cps.set("3")
    app._clear_hotkey()
    app._reset_defaults()
    assert app._cps.get() == "10"
    assert app._hotkey_label.get() == "F8"
    assert app._button.get() == "left"


def test_settings_are_persisted_and_reloaded(tmp_path):
    from app import AutoClickerApp

    first = AutoClickerApp(mouse=FakeMouse(), config_path=tmp_path / "settings.json")
    first._cps.set("27")
    first._button.set("right")
    first._jitter_text.set("30")
    first._save()
    pump(first, 0.05)
    first._on_close()

    second = AutoClickerApp(mouse=FakeMouse(), config_path=tmp_path / "settings.json")
    try:
        assert second._cps.get() == "27"
        assert second._button.get() == "right"
        assert second._jitter_text.get() == "30"
    finally:
        second._on_close()


def test_inputs_are_locked_while_running(gui):
    app, _ = gui
    app.start()
    pump(app, 0.1)
    assert str(app._cps_entry.cget("state")) == "disabled"
    app.stop()
    pump(app, 0.2)
    assert str(app._cps_entry.cget("state")) == "normal"


def test_hook_reported_in_log(gui):
    app, _ = gui
    assert "podsłuch" in log_text(app).lower() or "Klikanie wyłączone" in log_text(app)
