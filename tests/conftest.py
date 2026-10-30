import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest


class FakeMouse:
    def __init__(self, position=(400, 300)):
        self.press_log = []
        self.move_log = []
        self._position = position
        self.fail_after = None

    def click(self, button, count=1):
        if self.fail_after is not None and len(self.press_log) >= self.fail_after:
            raise RuntimeError("mysz odmówiła współpracy")
        self.press_log.extend([button] * max(1, count))

    def position(self):
        return self._position

    def move(self, position):
        self.move_log.append(position)
        self._position = position

    @property
    def left(self):
        return self.press_log.count("left")

    @property
    def right(self):
        return self.press_log.count("right")


@pytest.fixture
def mouse():
    return FakeMouse()
