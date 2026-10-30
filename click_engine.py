from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Protocol, Sequence, Tuple

LEFT = "left"
RIGHT = "right"
BOTH = "both"

MIN_CPS = 0.1
MAX_CPS = 100.0

BUTTON_SEQUENCE: Dict[str, Tuple[str, ...]] = {
    LEFT: (LEFT,),
    RIGHT: (RIGHT,),
    BOTH: (LEFT, RIGHT),
}

BUTTON_LABELS: Dict[str, str] = {
    LEFT: "lewy",
    RIGHT: "prawy",
    BOTH: "lewy + prawy",
}


class Mouse(Protocol):
    def click(self, button: str, count: int = 1) -> None:
        ...

    def position(self) -> Optional[Tuple[int, int]]:
        ...

    def move(self, position: Tuple[int, int]) -> None:
        ...


def clamp_cps(value: float) -> float:
    return min(MAX_CPS, max(MIN_CPS, value))


def clamp_jitter(value: float) -> float:
    return min(0.9, max(0.0, value))


@dataclass
class ClickSettings:
    button: str = LEFT
    cps: float = 10.0
    double_click: bool = False
    jitter: float = 0.0
    total_clicks: int = 0
    position: Optional[Tuple[int, int]] = None
    restore_cursor: bool = False

    @property
    def interval(self) -> float:
        return 1.0 / clamp_cps(self.cps)

    @property
    def buttons(self) -> Sequence[str]:
        return BUTTON_SEQUENCE.get(self.button, BUTTON_SEQUENCE[LEFT])

    @property
    def clicks_per_press(self) -> int:
        return 2 if self.double_click else 1


@dataclass
class ClickResult:
    clicks: int
    duration: float
    error: Optional[str] = None

    @property
    def cps(self) -> float:
        if self.duration <= 0:
            return 0.0
        return self.clicks / self.duration


class ClickEngine:
    def __init__(
        self,
        mouse: Mouse,
        settings: ClickSettings,
        on_finish: Optional[Callable[[ClickResult], None]] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.mouse = mouse
        self.settings = settings
        self.on_finish = on_finish
        self._rng = rng or random.Random()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.clicks = 0
        self.error: Optional[str] = None
        self.started_at = 0.0
        self.finished_at = 0.0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def elapsed(self) -> float:
        if self.started_at <= 0:
            return 0.0
        return (self.finished_at or time.perf_counter()) - self.started_at

    @property
    def current_cps(self) -> float:
        if self.elapsed <= 0:
            return 0.0
        return self.clicks / self.elapsed

    @property
    def remaining(self) -> Optional[int]:
        limit = self.settings.total_clicks
        if limit <= 0:
            return None
        return max(0, limit - self.clicks)

    def start(self) -> bool:
        if self.running:
            return False
        self._stop.clear()
        self.clicks = 0
        self.error = None
        self.finished_at = 0.0
        self.started_at = time.perf_counter()
        self._thread = threading.Thread(target=self._run, name="autoclicker-engine", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def _remaining(self) -> int:
        limit = self.settings.total_clicks
        if limit <= 0:
            return self.settings.clicks_per_press
        return min(self.settings.clicks_per_press, limit - self.clicks)

    def _click(self) -> None:
        position = self.settings.position
        original = self.mouse.position() if position is not None and self.settings.restore_cursor else None
        if position is not None:
            self.mouse.move(position)
        for button in self.settings.buttons:
            count = self._remaining()
            if count <= 0:
                break
            self.mouse.click(button, count)
            self.clicks += count
        if position is not None and original is not None:
            self.mouse.move(original)

    def _run(self) -> None:
        settings = self.settings
        interval = settings.interval
        jitter = clamp_jitter(settings.jitter)
        limit = settings.total_clicks
        next_at = time.perf_counter() + interval
        try:
            while not self._stop.is_set():
                if limit > 0 and self.clicks >= limit:
                    break
                self._click()
                if limit > 0 and self.clicks >= limit:
                    break
                delay = next_at - time.perf_counter()
                if jitter > 0:
                    delay = max(0.0, delay * (1.0 + self._rng.uniform(-jitter, jitter)))
                if delay > 0:
                    self._stop.wait(delay)
                next_at += interval
                if time.perf_counter() - next_at > interval * 2:
                    next_at = time.perf_counter()
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
        finally:
            self.finished_at = time.perf_counter()
            if self.on_finish is not None:
                self.on_finish(ClickResult(self.clicks, self.elapsed, self.error))
