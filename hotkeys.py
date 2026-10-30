from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

MODIFIER_NAMES = {
    "shift",
    "shift_l",
    "shift_r",
    "ctrl",
    "ctrl_l",
    "ctrl_r",
    "control",
    "control_l",
    "control_r",
    "alt",
    "alt_l",
    "alt_r",
    "alt_gr",
    "cmd",
    "cmd_r",
    "caps_lock",
    "num_lock",
    "scroll_lock",
}

KEY_LABELS: Dict[str, str] = {
    "alt": "Alt",
    "alt_gr": "AltGr",
    "alt_l": "Lewy Alt",
    "alt_r": "Prawy Alt",
    "backspace": "Backspace",
    "caps_lock": "Caps Lock",
    "cmd": "Cmd",
    "cmd_r": "Prawy Cmd",
    "control": "Ctrl",
    "control_l": "Lewy Ctrl",
    "control_r": "Prawy Ctrl",
    "delete": "Delete",
    "down": "↓",
    "end": "End",
    "enter": "Enter",
    "esc": "Esc",
    "home": "Home",
    "insert": "Insert",
    "left": "←",
    "num_lock": "Num Lock",
    "page_down": "Page Down",
    "page_up": "Page Up",
    "pause": "Pause",
    "print_screen": "Print Screen",
    "right": "→",
    "scroll_lock": "Scroll Lock",
    "shift": "Shift",
    "shift_l": "Lewy Shift",
    "shift_r": "Prawy Shift",
    "space": "Spacja",
    "tab": "Tab",
    "up": "↑",
}

CHAR_KEYSYMS: Dict[str, str] = {
    "!": "exclam",
    "\"": "quotedbl",
    "#": "numbersign",
    "$": "dollar",
    "%": "percent",
    "&": "ampersand",
    "'": "apostrophe",
    "(": "parenleft",
    ")": "parenright",
    "*": "asterisk",
    "+": "plus",
    ",": "comma",
    "-": "minus",
    ".": "period",
    "/": "slash",
    ":": "colon",
    ";": "semicolon",
    "<": "less",
    "=": "equal",
    ">": "greater",
    "?": "question",
    "@": "at",
    "[": "bracketleft",
    "\\": "backslash",
    "]": "bracketright",
    "^": "asciicircum",
    "_": "underscore",
    "`": "grave",
    "{": "braceleft",
    "|": "bar",
    "}": "braceright",
    "~": "asciitilde",
}

TK_KEYSYMS: Dict[str, str] = {
    "backspace": "BackSpace",
    "delete": "Delete",
    "down": "Down",
    "end": "End",
    "enter": "Return",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "left": "Left",
    "page_down": "Next",
    "page_up": "Prior",
    "pause": "Pause",
    "print_screen": "Print",
    "right": "Right",
    "space": "space",
    "tab": "Tab",
    "up": "Up",
    "num_lock": "Num_Lock",
    "scroll_lock": "Scroll_Lock",
    "caps_lock": "Caps_Lock",
    "shift_l": "Shift_L",
    "shift_r": "Shift_R",
    "control_l": "Control_L",
    "control_r": "Control_R",
    "alt_l": "Alt_L",
    "alt_r": "Alt_R",
    "meta_l": "Meta_L",
    "cmd": "Cmd",
}


KEY_NAME_ALIASES: Dict[str, str] = {
    "return": "enter",
    "linefeed": "enter",
    "kp_enter": "enter",
    "escape": "esc",
    "prior": "page_up",
    "next": "page_down",
    "break": "pause",
    "print": "print_screen",
    "sys_req": "print_screen",
    "menu": "apps",
    "win_l": "cmd",
    "win_r": "cmd_r",
    "ctrl": "control",
    "voidsymbol": None,
}


def canonical_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    key = name.lower()
    if key in KEY_NAME_ALIASES:
        value = KEY_NAME_ALIASES[key]
        return value
    return key


def normalise_char(char: Optional[str]) -> Optional[str]:
    if char is None or len(char) != 1 or not char.isprintable():
        return None
    if char.isalpha():
        return char.lower()
    return char


def is_function_key(name: str) -> bool:
    return name.startswith("f") and name[1:].isdigit() and 1 < len(name) < 4


def key_label(name: Optional[str], char: Optional[str]) -> str:
    if char is not None:
        return "Spacja" if char == " " else char.upper()
    if name is not None:
        if is_function_key(name):
            return name.upper()
        return KEY_LABELS.get(name, name.replace("_", " ").upper())
    return "?"


def tk_keysym(name: Optional[str], char: Optional[str]) -> Optional[str]:
    if name is not None:
        if is_function_key(name):
            return name.upper()
        return TK_KEYSYMS.get(name)
    if char is None:
        return None
    if char.isalnum():
        return char
    return CHAR_KEYSYMS.get(char)


@dataclass(frozen=True)
class KeyBinding:
    label: str
    name: Optional[str] = None
    char: Optional[str] = None
    vk: Optional[int] = None
    keysym: Optional[str] = None

    @property
    def is_modifier(self) -> bool:
        return self.name in MODIFIER_NAMES or (self.keysym or "").casefold() in {
            "shift_l",
            "shift_r",
            "control_l",
            "control_r",
            "alt_l",
            "alt_r",
            "meta_l",
            "meta_r",
            "caps_lock",
        }

    @property
    def tk_sequence(self) -> Optional[str]:
        if self.keysym is None:
            return None
        return f"<KeyPress-{self.keysym}>"

    def matches_key(self, key: Any) -> bool:
        name = canonical_name(getattr(key, "name", None))
        if name is not None and self.name is not None and name == self.name:
            return True
        char = normalise_char(getattr(key, "char", None))
        return char is not None and self.char is not None and char == self.char

    def matches_event(self, event: Any) -> bool:
        raw_keysym = getattr(event, "keysym", "") or ""
        keysym = raw_keysym.casefold()
        if keysym and self.keysym and keysym == self.keysym.casefold():
            return True
        if keysym and self.name and keysym == self.name:
            return True
        char = normalise_char(getattr(event, "char", ""))
        return char is not None and self.char is not None and char == self.char

    def as_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "name": self.name,
            "char": self.char,
            "vk": self.vk,
            "keysym": self.keysym,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["KeyBinding"]:
        if not isinstance(data, dict):
            return None
        label = data.get("label")
        if not label:
            return None
        return cls(
            label=str(label),
            name=canonical_name(data.get("name")),
            char=normalise_char(data.get("char")),
            vk=data.get("vk"),
            keysym=data.get("keysym"),
        )

    @classmethod
    def from_key(cls, key: Any) -> "KeyBinding":
        name = canonical_name(getattr(key, "name", None))
        char = normalise_char(getattr(key, "char", None))
        vk = getattr(key, "vk", None) or None
        return cls(
            label=key_label(name, char),
            name=name,
            char=char,
            vk=vk,
            keysym=tk_keysym(name, char),
        )

    @classmethod
    def from_event(cls, event: Any) -> "KeyBinding":
        keysym = getattr(event, "keysym", "") or ""
        char = normalise_char(getattr(event, "char", ""))
        name = canonical_name(keysym)
        vk = getattr(event, "keycode", None) or None
        return cls(
            label=key_label(name if char is None else char, char),
            name=name,
            char=char,
            vk=vk,
            keysym=keysym or tk_keysym(name, char),
        )


class HotkeyHook:
    def __init__(
        self,
        on_press: Callable[[Any], None],
        on_release: Optional[Callable[[Any], None]] = None,
    ) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._listener: Any = None
        self.failed = False

    @property
    def active(self) -> bool:
        return self._listener is not None

    def start(self) -> bool:
        if self._listener is not None:
            return True
        try:
            from pynput import keyboard
        except Exception:
            self.failed = True
            return False
        try:
            listener = keyboard.Listener(
                on_press=self._handle_press,
                on_release=self._handle_release,
            )
            listener.daemon = True
            listener.start()
        except Exception:
            self.failed = True
            return False
        self._listener = listener
        return True

    def stop(self) -> None:
        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass

    def _handle_press(self, key: Any) -> None:
        self._on_press(key)

    def _handle_release(self, key: Any) -> None:
        if self._on_release is not None:
            self._on_release(key)
