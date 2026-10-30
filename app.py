from __future__ import annotations

import queue
import sys
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple

import theme
from click_engine import (
    BOTH,
    BUTTON_LABELS,
    LEFT,
    MAX_CPS,
    MIN_CPS,
    RIGHT,
    ClickEngine,
    ClickResult,
    ClickSettings,
)
from hotkeys import HotkeyHook, KeyBinding
from mouse_backend import MouseUnavailable, PynputMouse
from paths import APP_NAME, APP_VERSION, resource_path
from settings import build_settings, hotkey_from, load, parse_number, parse_int, save, values_with_hotkey

EMERGENCY_KEYS = ("F10",)
EMERGENCY_VK = 121
SAVE_DELAY_MS = 400
POLL_INTERVAL_MS = 60
TRIGGER_DEBOUNCE_S = 0.05
STALE_KEY_DOWN_S = 1.5
CPS_PRESETS = ("1", "5", "10", "20", "50")
MAX_JITTER_PERCENT = 90
DEFAULT_HOTKEY = KeyBinding(label="F8", name="f8", char=None, vk=119, keysym="F8")

def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs} s"

def format_number(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"

class AutoClickerApp(tk.Tk):
    def __init__(self, mouse: Any = None, config_path: Any = None) -> None:
        super().__init__()
        self._config_path = config_path
        self._stored = load(config_path)
        self._mouse_error: Optional[str] = None
        self.mouse = mouse if mouse is not None else self._create_mouse()
        self.title(APP_NAME)
        self.configure(bg=theme.BG)
        theme.apply_theme(self)
        self._use_native_icons()

        self._engine: Optional[ClickEngine] = None
        self._result: Optional[ClickResult] = None
        self._inputs: List[Any] = []
        self._local_sequences: List[str] = []
        self._capturing = False
        self._key_down = False
        self._key_down_at = 0.0
        self._last_trigger = 0.0
        self._poll_job: Optional[str] = None
        self._fit_job: Optional[str] = None
        self._save_job: Optional[str] = None
        self._hook_status = ""
        self._key_queue: "queue.SimpleQueue" = queue.SimpleQueue()
        self._result_queue: "queue.SimpleQueue" = queue.SimpleQueue()

        self._build_vars()
        self._build_ui()
        self._build_hook()
        self._bind_local_hotkey()
        self._sync_inputs_state()
        self._refresh_summary()
        if self.mouse is None:
            self._log_line("Klikanie wyłączone: brak dostępu do myszy.", "warn")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<FocusOut>", self._on_focus_out)
        self._fit_job = self.after(80, self._fit_window)
        self._poll_job = self.after(POLL_INTERVAL_MS, self._poll)

    @property
    def engine(self) -> Optional[ClickEngine]:
        return self._engine

    @property
    def running(self) -> bool:
        return self._engine is not None and self._engine.running

    @property
    def hook_active(self) -> bool:
        return self._hook.active

    def _create_mouse(self) -> Any:
        try:
            return PynputMouse()
        except MouseUnavailable as exc:
            self._mouse_error = str(exc)
            return None

    def _use_native_icons(self) -> None:
        icon = resource_path("icon.ico")
        if sys.platform == "win32" and icon.exists():
            try:
                self.iconbitmap(default=str(icon))
                return
            except tk.TclError:
                pass
        png = resource_path("icon.png")
        if png.exists():
            try:
                self._icon_image = tk.PhotoImage(file=str(png))
                self.iconphoto(True, self._icon_image)
            except tk.TclError:
                pass

    def _fit_window(self) -> None:
        self._fit_job = None
        self.update_idletasks()
        width = max(760, self.winfo_reqwidth() + 28)
        height = max(520, self.winfo_reqheight() + 16)
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 4)
        self.minsize(width, height)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_vars(self) -> None:
        stored = self._stored
        self._button = tk.StringVar(value=stored["button"])
        self._cps = tk.StringVar(value=stored["cps"])
        self._double = tk.BooleanVar(value=stored["double_click"])
        self._limit = tk.StringVar(value=stored["limit"])
        self._jitter_text = tk.StringVar(value=str(parse_int(stored["jitter"], 0)))
        self._position_mode = tk.StringVar(value=stored["position_mode"])
        self._pos_x = tk.StringVar(value=stored["position_x"])
        self._pos_y = tk.StringVar(value=stored["position_y"])
        self._restore_cursor = tk.BooleanVar(value=stored["restore_cursor"])
        self._mode = tk.StringVar(value=stored["hotkey_mode"])
        self._hotkey = hotkey_from(stored) or DEFAULT_HOTKEY
        self._hotkey_label = tk.StringVar(value=self._hotkey.label)
        self._watched_vars = [
            self._button,
            self._cps,
            self._double,
            self._limit,
            self._jitter_text,
            self._position_mode,
            self._pos_x,
            self._pos_y,
            self._restore_cursor,
            self._mode,
        ]
        for variable in self._watched_vars:
            variable.trace_add("write", self._on_value_change)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=11)
        self.columnconfigure(1, weight=8)
        self.rowconfigure(1, weight=1)
        self._build_header()
        left = ttk.Frame(self)
        left.grid(row=1, column=0, sticky="n", padx=(18, 8), pady=(0, 12))
        left.columnconfigure(0, weight=1)
        right = ttk.Frame(self)
        right.grid(row=1, column=1, sticky="ns", padx=(8, 18), pady=(0, 12))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        self._build_click_card(left, 0)
        self._build_position_card(left, 1)
        self._build_hotkey_card(left, 2)
        self._build_control_card(right, 0)
        self._build_log_card(right, 1)
        self._build_footer()

    def _card(self, parent: tk.Misc, title: str, row: int, sticky: str = "ew") -> ttk.Frame:
        card = tk.Frame(parent, bg=theme.CARD, highlightbackground=theme.CARD_BORDER, highlightthickness=1)
        card.grid(row=row, column=0, sticky=sticky)
        body = ttk.Frame(card, style="Card.TFrame", padding=(18, 15))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text=title.upper(), style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))
        content = ttk.Frame(body, style="Card.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(1, weight=1)
        content.columnconfigure(0, weight=1)
        return content

    def _line(self, parent: tk.Misc, row: int) -> ttk.Frame:
        line = ttk.Frame(parent, style="Card.TFrame")
        line.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        return line

    def _caption(self, parent: tk.Misc, text: str) -> ttk.Label:
        return ttk.Label(parent, text=text, style="Muted.TLabel")

    def _segment(self, parent: tk.Misc, variable: tk.Variable, *options: Tuple[str, str]) -> None:
        box = ttk.Frame(parent, style="Card.TFrame")
        box.pack(side="left")
        for text, value in options:
            widget = ttk.Radiobutton(box, text=text, value=value, variable=variable, style="Segment.TRadiobutton")
            widget.pack(side="left", padx=(0, 5))
            self._inputs.append(widget)

    def _build_header(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(18, 14))
        header.columnconfigure(0, weight=1)
        title_box = ttk.Frame(header)
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(title_box, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(title_box, text=f"  v{APP_VERSION}", style="Version.TLabel").pack(side="left")
        self._status = tk.Label(
            header,
            text="●  GOTOWY",
            bg=theme.FIELD,
            fg=theme.MUTED,
            font=(theme.FONT, theme.SIZE, "bold"),
            width=12,
            anchor="center",
            padx=14,
            pady=8,
        )
        self._status.grid(row=0, column=1, sticky="e")

    def _build_click_card(self, parent: tk.Misc, row: int) -> None:
        content = self._card(parent, "Klikanie", row)

        buttons = self._line(content, 0)
        self._caption(buttons, "Przycisk myszy").pack(side="left", padx=(0, 14))
        self._segment(buttons, self._button, ("Lewy", LEFT), ("Prawy", RIGHT), ("Oba", BOTH))
        self._caption(buttons, "  „Oba” = lewy i prawy").pack(side="left")

        cps_row = self._line(content, 1)
        self._caption(cps_row, "CPS (klików/s)").pack(side="left", padx=(0, 14))
        stepper = ttk.Frame(cps_row, style="Card.TFrame")
        stepper.pack(side="left")
        ttk.Button(stepper, text="−", width=3, style="Chip.TButton", command=lambda: self._bump_cps(-1)).pack(side="left")
        self._cps_entry = ttk.Entry(stepper, textvariable=self._cps, width=7, justify="center", font=(theme.FONT, 11, "bold"))
        self._cps_entry.pack(side="left", padx=6)
        self._cps_entry.bind("<Return>", lambda event: self._normalise_cps())
        self._cps_entry.bind("<FocusOut>", lambda event: self._normalise_cps())
        ttk.Button(stepper, text="+", width=3, style="Chip.TButton", command=lambda: self._bump_cps(1)).pack(side="left")
        presets = ttk.Frame(cps_row, style="Card.TFrame")
        presets.pack(side="left", padx=(18, 0))
        for value in CPS_PRESETS:
            ttk.Button(presets, text=value, width=3, style="Chip.TButton", command=lambda v=value: self._set_cps(v)).pack(
                side="left", padx=(0, 4)
            )
        self._inputs.append(self._cps_entry)

        options_row = self._line(content, 2)
        ttk.Checkbutton(options_row, text="Podwójne kliknięcie", variable=self._double).pack(side="left")
        self._caption(options_row, "   Limit kliknięć").pack(side="left")
        self._limit_entry = ttk.Entry(options_row, textvariable=self._limit, width=7, justify="center")
        self._limit_entry.pack(side="left", padx=(8, 6))
        self._caption(options_row, "0 = bez limitu").pack(side="left", padx=(0, 18))
        self._inputs.append(self._limit_entry)

        jitter_row = self._line(content, 3)
        self._caption(jitter_row, "Losowość odstępów").pack(side="left", padx=(0, 14))
        jitter_box = ttk.Frame(jitter_row, style="Card.TFrame")
        jitter_box.pack(side="left")
        ttk.Button(jitter_box, text="−", width=3, style="Chip.TButton", command=lambda: self._bump_jitter(-5)).pack(side="left")
        self._jitter_entry = ttk.Entry(jitter_box, textvariable=self._jitter_text, width=5, justify="center")
        self._jitter_entry.pack(side="left", padx=6)
        self._jitter_entry.bind("<Return>", lambda event: self._normalise_jitter())
        self._jitter_entry.bind("<FocusOut>", lambda event: self._normalise_jitter())
        ttk.Button(jitter_box, text="+", width=3, style="Chip.TButton", command=lambda: self._bump_jitter(5)).pack(side="left")
        self._jitter_label = ttk.Label(jitter_row, text="", style="Muted.TLabel")
        self._jitter_label.pack(side="left", padx=(12, 0))
        self._inputs.append(self._jitter_entry)
        self._update_jitter_label()

    def _build_position_card(self, parent: tk.Misc, row: int) -> None:
        content = self._card(parent, "Pozycja", row)

        modes = self._line(content, 0)
        self._caption(modes, "Klikam").pack(side="left", padx=(0, 14))
        self._segment(modes, self._position_mode, ("Pod kursorem", "cursor"), ("W stałym miejscu", "fixed"))

        coords = self._line(content, 1)
        self._caption(coords, "Współrzędne").pack(side="left", padx=(0, 14))
        fields = ttk.Frame(coords, style="Card.TFrame")
        fields.pack(side="left")
        self._pos_x_entry = ttk.Entry(fields, textvariable=self._pos_x, width=7, justify="center")
        self._pos_x_entry.pack(side="left")
        self._caption(fields, "X").pack(side="left", padx=(4, 16))
        self._pos_y_entry = ttk.Entry(fields, textvariable=self._pos_y, width=7, justify="center")
        self._pos_y_entry.pack(side="left")
        self._caption(fields, "Y").pack(side="left", padx=(4, 0))
        self._inputs.extend([self._pos_x_entry, self._pos_y_entry])
        ttk.Button(coords, text="Pobierz z kursora", style="Chip.TButton", command=self._grab_cursor_position).pack(
            side="left", padx=(16, 0)
        )

        extra = self._line(content, 2)
        ttk.Checkbutton(extra, text="Przywróć kursor w stare miejsce po kliknięciu", variable=self._restore_cursor).pack(side="left")

    def _build_hotkey_card(self, parent: tk.Misc, row: int) -> None:
        content = self._card(parent, "Skrót", row)

        keys = self._line(content, 0)
        self._caption(keys, "Klawisz").pack(side="left", padx=(0, 14))
        self._hotkey_chip = tk.Label(
            keys,
            textvariable=self._hotkey_label,
            bg=theme.FIELD,
            fg=theme.TEXT,
            font=(theme.FONT, 11, "bold"),
            padx=18,
            pady=7,
            highlightbackground=theme.FIELD_BORDER,
            highlightthickness=1,
        )
        self._hotkey_chip.pack(side="left", padx=(0, 16))
        actions = ttk.Frame(keys, style="Card.TFrame")
        actions.pack(side="left")
        ttk.Button(actions, text="Przypisz klawisz", style="Chip.TButton", command=self._capture_hotkey).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Wyczyść", style="Chip.TButton", command=self._clear_hotkey).pack(side="left")
        modes = self._line(content, 1)
        self._caption(modes, "Tryb").pack(side="left", padx=(0, 14))
        self._segment(modes, self._mode, ("Przełącznik", "toggle"), ("Przytrzymanie", "hold"))

        self._hotkey_hint = ttk.Label(content, text="", style="Muted.TLabel")
        self._hotkey_hint.grid(row=2, column=0, sticky="w", pady=(4, 0))

    def _build_control_card(self, parent: tk.Misc, row: int) -> None:
        card = tk.Frame(parent, bg=theme.CARD, highlightbackground=theme.CARD_BORDER, highlightthickness=1)
        card.grid(row=row, column=0, sticky="ew")
        body = ttk.Frame(card, style="Card.TFrame", padding=(18, 16))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        self._toggle_button = ttk.Button(body, text="START", style="Primary.TButton", command=self.toggle)
        self._toggle_button.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        stats = ttk.Frame(body, style="Card.TFrame")
        stats.grid(row=1, column=0, sticky="ew")
        for index in range(3):
            stats.columnconfigure(index, weight=1)
        self._stat_clicks = self._stat(stats, 0, "KLIKNIĘCIA", "0")
        self._stat_time = self._stat(stats, 1, "CZAS", "0 s")
        self._stat_cps = self._stat(stats, 2, "REALNE CPS", "0.00")
        ttk.Separator(body, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(16, 12))
        self._info = ttk.Label(body, text="", style="Muted.TLabel", justify="left", wraplength=330)
        self._info.grid(row=3, column=0, sticky="w")
        self._key_label = ttk.Label(body, text="", style="Muted.TLabel", justify="left", wraplength=330)
        self._key_label.grid(row=4, column=0, sticky="w", pady=(8, 0))

    def _stat(self, parent: tk.Misc, column: int, caption: str, value: str) -> ttk.Label:
        box = ttk.Frame(parent, style="Card.TFrame")
        box.grid(row=0, column=column, sticky="w")
        label = ttk.Label(box, text=value, style="Stat.TLabel")
        label.grid(row=0, column=0, sticky="w")
        ttk.Label(box, text=caption, style="Caption.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        return label

    def _build_log_card(self, parent: tk.Misc, row: int) -> None:
        card = tk.Frame(parent, bg=theme.CARD, highlightbackground=theme.CARD_BORDER, highlightthickness=1)
        card.grid(row=row, column=0, sticky="nsew")
        body = ttk.Frame(card, style="Card.TFrame", padding=(18, 15))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        ttk.Label(body, text="DZIENNIK", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._log = tk.Text(
            body,
            width=38,
            height=9,
            bg=theme.FIELD,
            fg=theme.TEXT,
            insertbackground=theme.TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=(theme.FONT, 9),
            padx=10,
            pady=8,
            state="disabled",
            wrap="word",
        )
        self._log.grid(row=1, column=0, sticky="nsew")
        self._log.tag_configure("time", foreground=theme.MUTED)
        self._log.tag_configure("warn", foreground=theme.AMBER)
        self._log.tag_configure("stop", foreground=theme.DANGER)
        self._log.tag_configure("go", foreground=theme.OK)

    def _build_footer(self) -> None:
        footer = ttk.Frame(self)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 16))
        footer.columnconfigure(0, weight=1)
        self._footer_hint = ttk.Label(footer, text="", style="Hint.TLabel")
        self._footer_hint.grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Przywróć domyślne", style="Ghost.TButton", command=self._reset_defaults).grid(
            row=0, column=1, sticky="e"
        )

    def _log_line(self, text: str, tag: str = "") -> None:
        self._log.configure(state="normal")
        self._log.insert("end", f"{time.strftime('%H:%M:%S')}  ", "time")
        self._log.insert("end", f"{text}\n", tag)
        lines = int(self._log.index("end-1c").split(".")[0])
        if lines > 160:
            self._log.delete("1.0", f"{lines - 100}.0")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _on_value_change(self, *_args: Any) -> None:
        self._update_jitter_label()
        self._sync_inputs_state()
        self._refresh_summary()
        self._schedule_save()

    def _refresh_summary(self) -> None:
        if self.running:
            return
        settings = build_settings(self._current_values())
        self._set_text(self._info, self._summary(settings))

    def _summary(self, settings: ClickSettings, remaining: Optional[int] = None) -> str:
        parts = [f"{format_number(settings.cps)} CPS", BUTTON_LABELS[settings.button]]
        if settings.double_click:
            parts.append("podwójne kliknięcie")
        if settings.jitter:
            parts.append(f"±{int(settings.jitter * 100)}% losowości")
        if settings.total_clicks > 0:
            parts.append(f"limit {settings.total_clicks}")
        if settings.position is not None:
            parts.append(f"pozycja {settings.position[0]}, {settings.position[1]}")
        if remaining is not None:
            parts.append(f"pozostało {remaining}")
        return "  •  ".join(parts)

    def _schedule_save(self) -> None:
        if self._save_job is not None:
            self.after_cancel(self._save_job)
        self._save_job = self.after(SAVE_DELAY_MS, self._save)

    def _persist(self) -> None:
        self._stored = values_with_hotkey(self._current_values(), self._hotkey)
        save(self._stored, self._config_path)

    def _save(self) -> None:
        self._save_job = None
        self._persist()

    def _current_values(self) -> Dict[str, Any]:
        return {
            "button": self._button.get(),
            "cps": self._cps.get(),
            "double_click": self._double.get(),
            "jitter": self._jitter_text.get(),
            "limit": self._limit.get(),
            "position_mode": self._position_mode.get(),
            "position_x": self._pos_x.get(),
            "position_y": self._pos_y.get(),
            "restore_cursor": self._restore_cursor.get(),
            "hotkey_mode": self._mode.get(),
            "hotkey": self._hotkey.as_dict() if self._hotkey is not None else None,
        }

    def _set_cps(self, value: str) -> None:
        self._cps.set(value)
        self._normalise_cps()

    def _bump_cps(self, delta: int) -> None:
        current = parse_number(self._cps.get(), 10.0)
        step = 0.5 if current <= 5 else 1.0
        self._cps.set(format_number(max(MIN_CPS, min(MAX_CPS, current + delta * step))))

    def _normalise_cps(self) -> None:
        self._cps.set(format_number(max(MIN_CPS, min(MAX_CPS, parse_number(self._cps.get(), 10.0)))))

    def _bump_jitter(self, delta: int) -> None:
        value = parse_int(self._jitter_text.get(), 0) + delta
        self._jitter_text.set(str(self._clamped_jitter(value)))

    def _normalise_jitter(self) -> None:
        self._jitter_text.set(str(self._clamped_jitter(parse_int(self._jitter_text.get(), 0))))

    def _clamped_jitter(self, value: int) -> int:
        return max(0, min(MAX_JITTER_PERCENT, value))

    def _update_jitter_label(self) -> None:
        value = parse_int(self._jitter_text.get(), 0)
        hint = "wyłączone" if value <= 0 else f"± {value}% przerw między klikami"
        self._jitter_label.configure(text=hint)

    def _grab_cursor_position(self) -> None:
        if self.mouse is None:
            self._log_line("Brak dostępu do myszy.", "warn")
            return
        position = self.mouse.position()
        if position is None:
            self._log_line("Nie udało się odczytać pozycji kursora.", "warn")
            return
        self._pos_x.set(str(int(position[0])))
        self._pos_y.set(str(int(position[1])))
        self._position_mode.set("fixed")
        self._log_line(f"Pobrano pozycję kursora: {int(position[0])}, {int(position[1])}.")

    def _build_hook(self) -> None:
        self._hook = HotkeyHook(self._on_hook_press, self._on_hook_release)
        if self._mouse_error:
            self._hook_status = self._mouse_error
            self._log_line(f"Skrót globalny niedostępny: {self._mouse_error}", "warn")
            return
        if self._hook.start():
            self._hook_status = "Globalny podsłuch klawiatury: aktywny."
        else:
            self._hook_status = "Globalny podsłuch klawiatury: niedostępny (skrót działa przy aktywnym oknie)."
        self._log_line(self._hook_status, "" if self._hook.active else "warn")

    def _bind_local_hotkey(self) -> None:
        for sequence in self._local_sequences:
            self.unbind_all(sequence)
        self._local_sequences = []
        for keysym in EMERGENCY_KEYS:
            self.bind_all(f"<KeyPress-{keysym}>", self._on_emergency_key)
            self._local_sequences.append(f"<KeyPress-{keysym}>")
        if self._hotkey is not None and self._hotkey.tk_sequence:
            press = self._hotkey.tk_sequence
            release = f"<KeyRelease-{self._hotkey.keysym}>"
            self.bind_all(press, self._on_window_press)
            self.bind_all(release, self._on_window_release)
            self._local_sequences.extend([press, release])
        self._update_hints()

    def _update_hints(self) -> None:
        action = "przytrzymaj" if self._mode.get() == "hold" else "wciśnij"
        if self._hotkey is None:
            self._hotkey_hint.configure(text="Kliknij „Przypisz klawisz”, aby ustawić skrót.")
            self._key_label.configure(text="Skrót nie ustawiony — użyj przycisku START/STOP.")
        else:
            effect = "startu i stopu" if self._mode.get() == "toggle" else "klikania przez cały czas trzymania"
            self._hotkey_hint.configure(text=f"{action} {self._hotkey.label} dla {effect}.")
            self._key_label.configure(text=f"Skrót: {self._hotkey.label} ({action})  •  awaryjny stop: F10")
        self._toggle_button.configure(text="START")
        self._footer_hint.configure(text=f"{self._hook_status}  Ustawienia zapisują się same.")

    def _capture_hotkey(self) -> None:
        if self.running:
            self._log_line("Zatrzymaj klikanie, aby zmienić skrót.", "warn")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Przypisz klawisz")
        dialog.configure(bg=theme.BG)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - 400) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - 170) // 2)
        dialog.geometry(f"400x170+{x}+{y}")
        box = ttk.Frame(dialog, style="Card.TFrame", padding=(24, 20))
        box.pack(fill="both", expand=True)
        box.columnconfigure(0, weight=1)
        ttk.Label(box, text="Naciśnij klawisz do klikania", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        preview = ttk.Label(box, text="…", style="Stat.TLabel")
        preview.grid(row=1, column=0, sticky="w", pady=(14, 6))
        ttk.Label(box, text="Esc anuluje. Ctrl, Alt i Shift nie mogą być skrótem.", style="Muted.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        self._capturing = True
        result: Dict[str, Any] = {}

        def on_press(event: tk.Event) -> str:
            if event.keysym == "Escape":
                return "break"
            binding = KeyBinding.from_event(event)
            if binding.is_modifier or binding.tk_sequence is None:
                preview.configure(text=f"{binding.label} — nie można przypisać")
                return "break"
            preview.configure(text=binding.label)
            result["binding"] = binding
            return "break"

        dialog.bind("<KeyPress>", on_press)
        dialog.focus_force()
        self.wait_window(dialog)
        self._capturing = False
        dialog.grab_release()
        dialog.destroy()
        binding = result.get("binding")
        if binding is not None:
            self._apply_hotkey(binding)

    def _apply_hotkey(self, binding: Optional[KeyBinding]) -> None:
        self._hotkey = binding
        self._hotkey_label.set("nie ustawiony" if binding is None else binding.label)
        self._bind_local_hotkey()
        self._schedule_save()
        self._log_line("Skrót wyczyszczony." if binding is None else f"Skrót ustawiony: {binding.label}")

    def _clear_hotkey(self) -> None:
        if self.running:
            self._log_line("Zatrzymaj klikanie, aby zmienić skrót.", "warn")
            return
        self._apply_hotkey(None)

    def _reset_defaults(self) -> None:
        if self.running:
            return
        self._button.set(LEFT)
        self._cps.set("10")
        self._double.set(False)
        self._limit.set("0")
        self._jitter_text.set("15")
        self._position_mode.set("cursor")
        self._pos_x.set("0")
        self._pos_y.set("0")
        self._restore_cursor.set(False)
        self._mode.set("toggle")
        self._apply_hotkey(DEFAULT_HOTKEY)
        self._update_jitter_label()
        self._log_line("Przywrócono ustawienia domyślne.")

    def _is_typing(self) -> bool:
        try:
            focused = self.focus_get()
        except (KeyError, tk.TclError):
            return False
        return isinstance(focused, (tk.Entry, ttk.Entry))

    def _on_focus_out(self, _event: Any = None) -> None:
        self._key_down = False

    def _accept_trigger(self) -> bool:
        if self._capturing or self.mouse is None or self._is_typing():
            return False
        now = time.perf_counter()
        if now - self._last_trigger < TRIGGER_DEBOUNCE_S:
            return False
        self._last_trigger = now
        return True

    def _on_hook_press(self, key: Any) -> None:
        self._key_queue.put((key, True))

    def _on_hook_release(self, key: Any) -> None:
        self._key_queue.put((key, False))

    def _drain_key_queue(self) -> None:
        while True:
            try:
                key, pressed = self._key_queue.get_nowait()
            except queue.Empty:
                return
            self._handle_hook_key(key, pressed)

    def _drain_result_queue(self) -> None:
        while True:
            try:
                result = self._result_queue.get_nowait()
            except queue.Empty:
                return
            self._on_engine_finished(result)

    def _handle_hook_key(self, key: Any, pressed: bool) -> None:
        if self._hotkey is not None and self._hotkey.matches_key(key):
            self._trigger(pressed)
            return
        if getattr(key, "name", None) in EMERGENCY_KEYS or getattr(key, "vk", None) == EMERGENCY_VK:
            if pressed:
                self.emergency_stop()

    def _on_window_press(self, event: tk.Event) -> Optional[str]:
        if self._hotkey is None or self._capturing or self._is_typing():
            return None
        if self._hotkey.matches_event(event):
            self._trigger(True)
            return "break"
        return None

    def _on_window_release(self, event: tk.Event) -> None:
        if self._hotkey is not None and not self._capturing and self._hotkey.matches_event(event):
            self._trigger(False)

    def _on_emergency_key(self, event: tk.Event) -> None:
        if event.keysym in EMERGENCY_KEYS:
            self.emergency_stop()

    def _trigger(self, pressed: bool) -> None:
        if not pressed:
            if self._key_down and self._mode.get() == "hold":
                self.stop("Stop (klawisz zwolniony).")
            self._key_down = False
            return
        if self._key_down and time.perf_counter() - self._key_down_at < STALE_KEY_DOWN_S:
            return
        if not self._accept_trigger():
            return
        self._key_down = True
        self._key_down_at = time.perf_counter()
        if self._mode.get() == "hold":
            if not self.running:
                self.start()
            return
        self.toggle()

    def toggle(self) -> None:
        if self.running:
            self.stop("Stop.")
        else:
            self.start()

    def validated_settings(self) -> Optional[ClickSettings]:
        settings = build_settings(self._current_values())
        if parse_number(self._cps.get(), MIN_CPS) < MIN_CPS:
            self._log_line(f"CPS musi wynosić co najmniej {MIN_CPS:g}.", "warn")
            return None
        if parse_int(self._pos_x.get(), 0) < 0 or parse_int(self._pos_y.get(), 0) < 0:
            self._log_line("Współrzędne X i Y nie mogą być ujemne.", "warn")
            return None
        self._cps.set(format_number(settings.cps))
        self._limit.set(str(settings.total_clicks))
        return settings

    def start(self) -> None:
        if self.running or self.mouse is None:
            return
        settings = self.validated_settings()
        if settings is None:
            return
        self._result = None
        self._engine = ClickEngine(self.mouse, settings, on_finish=self._result_queue.put)
        self._engine.start()
        suffix = " (podwójne)" if settings.double_click else ""
        self._log_line(f"Start: {format_number(settings.cps)} CPS, {BUTTON_LABELS[settings.button]}{suffix}.", "go")
        self._sync_inputs_state()

    def stop(self, message: str = "Stop.") -> None:
        if self._engine is not None:
            self._engine.stop()
            if message:
                self._log_line(message)

    def emergency_stop(self) -> None:
        if not self.running:
            return
        self._key_down = False
        self.stop("Awaryjny stop.")
        self.bell()

    def _on_engine_finished(self, result: ClickResult) -> None:
        self._result = result
        self._engine = None
        if result.error:
            self._log_line(f"Zatrzymane: {result.error}", "stop")
        elif result.clicks:
            self._log_line(
                f"Wykonano {result.clicks} kliknięć w {format_duration(result.duration)} ({format_number(result.cps)} CPS)."
            )
        self._set_text(self._stat_clicks, str(result.clicks))
        self._set_text(self._stat_time, format_duration(result.duration))
        self._set_text(self._stat_cps, format_number(result.cps))
        self._refresh_summary()
        self._sync_inputs_state()

    def _sync_inputs_state(self) -> None:
        state = "disabled" if self.running else "normal"
        for widget in self._inputs:
            try:
                widget.configure(state=state)
            except tk.TclError:
                continue
        fixed = self._position_mode.get() == "fixed"
        for widget in (self._pos_x_entry, self._pos_y_entry):
            widget.configure(state="normal" if fixed and not self.running else "disabled")
        self._update_toggle_button()

    def _update_toggle_button(self) -> None:
        if self.running:
            self._toggle_button.configure(text="STOP", style="Danger.TButton")
        else:
            self._toggle_button.configure(style="Primary.TButton")
            self._update_hints()

    def _poll(self) -> None:
        self._poll_job = self.after(POLL_INTERVAL_MS, self._poll)
        self._drain_key_queue()
        self._drain_result_queue()
        engine = self._engine
        if engine is not None and engine.running:
            limit = engine.settings.total_clicks
            self._set_text(self._stat_clicks, str(engine.clicks) if limit <= 0 else f"{engine.clicks} / {limit}")
            self._set_text(self._stat_time, format_duration(engine.elapsed))
            self._set_text(self._stat_cps, format_number(engine.current_cps))
            self._set_text(self._info, self._summary(engine.settings, engine.remaining))
            self._set_status("●  KLIKAM", theme.OK)
        else:
            self._set_status("●  GOTOWY", theme.MUTED)

    def _set_text(self, widget: ttk.Label, text: str) -> None:
        if widget.cget("text") != text:
            widget.configure(text=text)

    def _set_status(self, text: str, colour: str) -> None:
        if self._status.cget("text") != text:
            self._status.configure(text=text)
        if self._status.cget("fg") != colour:
            self._status.configure(fg=colour)

    def _on_close(self) -> None:
        for job in (self._poll_job, self._fit_job, self._save_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self._poll_job = self._fit_job = self._save_job = None
        self._persist()
        if self._engine is not None:
            self._engine.stop()
            self._engine.join(0.5)
        self._hook.stop()
        self.destroy()

def main() -> None:
    if sys.platform == "win32":
        import ctypes

        for awareness in (2, 1):
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(awareness)
                break
            except Exception:
                continue
    AutoClickerApp().mainloop()

if __name__ == "__main__":
    main()
