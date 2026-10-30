import os
import subprocess
import sys
import time
from pathlib import Path

from pynput import keyboard, mouse

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path("/tmp/autoclicker-e2e")
CONFIG.mkdir(exist_ok=True)
(CONFIG / "settings.json").write_text('{"cps": "30", "button": "right", "limit": "0"}', encoding="utf-8")

presses = []
listener = mouse.Listener(on_click=lambda x, y, b, s: presses.append((b, s)))
listener.start()
time.sleep(0.3)

env = dict(os.environ, DISPLAY=":99", AUTOCLICKER_CONFIG_DIR=str(CONFIG))
command = sys.argv[1:] or [sys.executable, "app.py"]
app = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
time.sleep(3.0)

keys = keyboard.Controller()


def tap(key):
    keys.press(key)
    time.sleep(0.06)
    keys.release(key)


tap(keyboard.Key.f8)
time.sleep(1.2)
during_start = len(presses)
tap(keyboard.Key.f8)
time.sleep(0.8)
during_stop = len(presses)
tap(keyboard.Key.f8)
time.sleep(0.8)
during_resume = len(presses)
tap(keyboard.Key.f10)
time.sleep(0.9)
after_panic = len(presses)
time.sleep(0.8)
after_settle = len(presses)

app.terminate()
try:
    output = app.communicate(timeout=5)[0]
except subprocess.TimeoutExpired:
    app.kill()
    output = ""
listener.stop()

print(f"events: start={during_start} po_stopie={during_stop} po_wznowie={during_resume} po_F10={after_panic} settled={after_settle}")
print("klikniecia w czasie klikania:", during_start)
print("przerwa po stop:", during_stop - during_start)
print("wznowienie:", during_resume - during_stop)
print("po awaryjnym stop (powinno = 0):", after_settle - after_panic)
print("app output:", repr(output[-600:]))
print("settings:", (CONFIG / "settings.json").read_text(encoding="utf-8"))
