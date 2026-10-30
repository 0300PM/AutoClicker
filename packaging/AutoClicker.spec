import os

from PyInstaller.utils.hooks import collect_submodules

PLATFORM_BACKENDS = [
    "pynput.keyboard._win32",
    "pynput.keyboard._uinput",
    "pynput.keyboard._darwin",
    "pynput.keyboard._xorg",
    "pynput.keyboard._dummy",
    "pynput.mouse._win32",
    "pynput.mouse._darwin",
    "pynput.mouse._xorg",
    "pynput.mouse._dummy",
]

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))
ASSETS = os.path.join(ROOT, "assets")

a = Analysis(
    [os.path.join(ROOT, "app.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ASSETS, "icon.ico"), "assets"), (os.path.join(ASSETS, "icon.png"), "assets")],
    hiddenimports=sorted(set(PLATFORM_BACKENDS) | set(collect_submodules("pynput"))) + ["six"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "PIL", "numpy", "scipy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AutoClicker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ASSETS, "icon.ico"),
)
