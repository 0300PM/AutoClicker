from __future__ import annotations

from tkinter import Tk
from tkinter import ttk

BG = "#161a22"
CARD = "#1f2530"
CARD_BORDER = "#2c3441"
FIELD = "#131820"
FIELD_BORDER = "#39445a"
TEXT = "#e9edf5"
MUTED = "#8d97ab"
ACCENT = "#4f8cff"
ACCENT_PRESSED = "#3a76e8"
DANGER = "#e14f5f"
DANGER_PRESSED = "#c53f4e"
OK = "#37d39a"
AMBER = "#ffc76b"
FONT = "Segoe UI"
SIZE = 10


def apply_theme(root: Tk) -> ttk.Style:
    root.configure(bg=BG)
    root.option_add("*Font", (FONT, SIZE))
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        background=BG,
        foreground=TEXT,
        fieldbackground=FIELD,
        bordercolor=FIELD_BORDER,
        lightcolor=BG,
        darkcolor=BG,
        troughcolor=FIELD,
        focuscolor=FIELD,
        arrowcolor=TEXT,
        font=(FONT, SIZE),
    )
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("Muted.TLabel", background=CARD, foreground=MUTED)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=(FONT, 15, "bold"))
    style.configure("Version.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
    style.configure("Stat.TLabel", background=CARD, foreground=TEXT, font=(FONT, 17, "bold"))
    style.configure("Caption.TLabel", background=CARD, foreground=MUTED, font=(FONT, 8))
    style.configure("Status.TLabel", background=BG, foreground=TEXT, font=(FONT, SIZE, "bold"))
    style.configure("Hint.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))

    style.configure(
        "TButton",
        background=CARD,
        foreground=TEXT,
        bordercolor=CARD_BORDER,
        lightcolor=CARD,
        darkcolor=CARD,
        focuscolor=CARD,
        relief="flat",
        padding=(12, 7),
        font=(FONT, SIZE, "bold"),
    )
    style.map(
        "TButton",
        background=[("disabled", BG), ("pressed", FIELD), ("active", "#28303d")],
        foreground=[("disabled", MUTED)],
        bordercolor=[("active", ACCENT), ("pressed", ACCENT)],
    )
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="#ffffff",
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        bordercolor=ACCENT,
        padding=(16, 10),
        font=(FONT, SIZE + 2, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", ACCENT_PRESSED), ("active", "#5f98ff")],
        bordercolor=[("active", ACCENT), ("pressed", ACCENT_PRESSED)],
    )
    style.configure("Danger.TButton", background=DANGER, lightcolor=DANGER, darkcolor=DANGER, bordercolor=DANGER)
    style.map(
        "Danger.TButton",
        background=[("pressed", DANGER_PRESSED), ("active", "#ea5f6e")],
        bordercolor=[("active", DANGER), ("pressed", DANGER_PRESSED)],
    )
    style.configure("Ghost.TButton", background=BG, bordercolor=BG, lightcolor=BG, darkcolor=BG, padding=(9, 4))
    style.map(
        "Ghost.TButton",
        background=[("active", "#28303d"), ("pressed", FIELD)],
        bordercolor=[("active", ACCENT)],
    )
    style.configure("Chip.TButton", background=FIELD, bordercolor=CARD_BORDER, padding=(8, 3), font=(FONT, 9))

    style.configure(
        "TEntry",
        fieldbackground=FIELD,
        foreground=TEXT,
        insertcolor=TEXT,
        bordercolor=FIELD_BORDER,
        lightcolor=FIELD,
        darkcolor=FIELD,
        relief="flat",
        padding=6,
    )
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", FIELD)], darkcolor=[("focus", FIELD)])

    style.configure(
        "Segment.TRadiobutton",
        background=FIELD,
        foreground=MUTED,
        bordercolor=CARD_BORDER,
        lightcolor=FIELD,
        darkcolor=FIELD,
        relief="flat",
        padding=(13, 7),
        font=(FONT, SIZE, "bold"),
    )
    style.map(
        "Segment.TRadiobutton",
        background=[("selected", ACCENT), ("active", "#28303d"), ("disabled", FIELD)],
        foreground=[("selected", "#ffffff"), ("active", TEXT), ("disabled", MUTED)],
        bordercolor=[("selected", ACCENT)],
    )

    style.configure(
        "TCheckbutton",
        background=CARD,
        foreground=TEXT,
        focuscolor=CARD,
        padding=(0, 3),
    )
    style.map(
        "TCheckbutton",
        background=[("active", CARD), ("disabled", CARD)],
        foreground=[("disabled", MUTED)],
        indicatorcolor=[("selected", ACCENT), ("active", FIELD)],
        bordercolor=[("selected", ACCENT)],
    )

    style.configure("TSeparator", background=CARD_BORDER, relief="flat")
    style.configure("TScale", background=CARD, troughcolor=FIELD, bordercolor=CARD)
    style.configure(
        "Horizontal.TScale",
        background=CARD,
        troughcolor=FIELD,
        sliderrelief="flat",
        sliderlength=16,
        bordercolor=CARD,
    )
    style.map("Horizontal.TScale", background=[("disabled", CARD)], troughcolor=[("disabled", CARD)])
    return style
