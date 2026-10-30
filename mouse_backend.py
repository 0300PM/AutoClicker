from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class MouseUnavailable(RuntimeError):
    pass


class PynputMouse:
    def __init__(self) -> None:
        try:
            from pynput.mouse import Button, Controller
        except Exception as exc:
            raise MouseUnavailable(f"Brak biblioteki pynput: {exc}") from exc
        self._buttons: Dict[str, Any] = {
            "left": Button.left,
            "right": Button.right,
        }
        self._controller = Controller()

    def click(self, button: str, count: int = 1) -> None:
        target = self._buttons.get(button, self._buttons["left"])
        for _ in range(max(1, count)):
            self._controller.click(target)

    def position(self) -> Optional[Tuple[int, int]]:
        try:
            x, y = self._controller.position
        except Exception:
            return None
        return int(round(x)), int(round(y))

    def move(self, position: Tuple[int, int]) -> None:
        self._controller.position = (int(position[0]), int(position[1]))
