import time

import pytest
from conftest import FakeMouse

from click_engine import (
    MAX_CPS,
    MIN_CPS,
    ClickEngine,
    ClickSettings,
    clamp_cps,
    clamp_jitter,
)


def run(engine, timeout=5.0):
    engine.start()
    deadline = time.monotonic() + timeout
    while engine.running and time.monotonic() < deadline:
        time.sleep(0.005)
    engine.stop()
    engine.join(1.0)
    assert time.monotonic() < deadline, "silnik nie zakończył pracy w czasie"
    return engine


def test_left_button_only():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(button="left", cps=60, total_clicks=12))
    run(engine)
    assert engine.clicks == 12
    assert mouse.press_log == ["left"] * 12
    assert mouse.right == 0


def test_right_button_only():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(button="right", cps=60, total_clicks=7))
    run(engine)
    assert mouse.press_log == ["right"] * 7


def test_both_buttons_alternate():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(button="both", cps=80, total_clicks=6))
    run(engine)
    assert engine.clicks == 6
    assert mouse.press_log == ["left", "right"] * 3


def test_limit_never_exceeded():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(button="both", cps=80, total_clicks=5))
    run(engine)
    assert engine.clicks == 5
    assert len(mouse.press_log) == 5


def test_double_click_sends_two_presses():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(button="left", cps=50, total_clicks=4, double_click=True))
    run(engine)
    assert engine.clicks == 4
    assert mouse.press_log == ["left"] * 4


def test_cps_controls_tempo():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(button="left", cps=20, total_clicks=21))
    started = time.perf_counter()
    run(engine)
    elapsed = time.perf_counter() - started
    assert 0.75 < elapsed < 1.9
    assert engine.clicks == 21
    assert 15 < engine.current_cps < 26


def test_stop_interrupts_unlimited_run():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(button="left", cps=40))
    engine.start()
    time.sleep(0.25)
    engine.stop()
    engine.join(1.0)
    assert engine.clicks > 3
    assert not engine.running
    assert len(mouse.press_log) == engine.clicks


def test_finish_callback_reports_result():
    seen = []
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(cps=80, total_clicks=3), on_finish=seen.append)
    run(engine)
    assert len(seen) == 1
    assert seen[0].clicks == 3
    assert seen[0].error is None
    assert seen[0].cps > 0


def test_mouse_error_is_reported_and_stops_run():
    mouse = FakeMouse()
    mouse.fail_after = 3
    engine = ClickEngine(mouse, ClickSettings(cps=80))
    run(engine, timeout=3.0)
    assert engine.error is not None
    assert "RuntimeError" in engine.error
    assert engine.clicks == 3


def test_fixed_position_moves_cursor_for_each_series():
    mouse = FakeMouse(position=(10, 10))
    engine = ClickEngine(mouse, ClickSettings(cps=80, total_clicks=2, position=(800, 600)))
    run(engine)
    assert mouse.move_log == [(800, 600), (800, 600)]


def test_restore_cursor_returns_to_original_place():
    mouse = FakeMouse(position=(10, 10))
    engine = ClickEngine(
        mouse,
        ClickSettings(button="left", cps=80, total_clicks=1, position=(800, 600), restore_cursor=True),
    )
    run(engine)
    assert mouse.move_log == [(800, 600), (10, 10)]
    assert mouse.position() == (10, 10)


def test_jitter_keeps_average_tempo():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(cps=25, total_clicks=26, jitter=0.4))
    started = time.perf_counter()
    run(engine)
    elapsed = time.perf_counter() - started
    assert 0.8 < elapsed < 1.6
    assert engine.clicks == 26


def test_remaining_counts_down_to_limit():
    mouse = FakeMouse()
    engine = ClickEngine(mouse, ClickSettings(cps=80, total_clicks=4))
    engine.start()
    assert engine.remaining is not None
    engine.stop()
    engine.join(1.0)


def test_remaining_is_none_without_limit():
    engine = ClickEngine(FakeMouse(), ClickSettings(cps=80))
    assert engine.remaining is None


def test_start_is_idempotent_while_running():
    engine = ClickEngine(FakeMouse(), ClickSettings(cps=80))
    assert engine.start() is True
    assert engine.start() is False
    engine.stop()
    engine.join(1.0)


def test_interval_respects_clamping():
    assert ClickSettings(cps=0).interval == pytest.approx(1 / MIN_CPS)
    assert ClickSettings(cps=10_000).interval == pytest.approx(1 / MAX_CPS)


def test_clamps():
    assert clamp_cps(-5) == MIN_CPS
    assert clamp_cps(9999) == MAX_CPS
    assert clamp_jitter(10) == 0.9
    assert clamp_jitter(-1) == 0.0


def test_elapsed_zero_before_start():
    engine = ClickEngine(FakeMouse(), ClickSettings())
    assert engine.elapsed == 0
    assert engine.current_cps == 0
    assert not engine.running
