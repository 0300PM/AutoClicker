from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
BACKGROUND_TOP = (38, 46, 62)
BACKGROUND_BOTTOM = (19, 23, 31)
BORDER = (72, 88, 118)
ACCENT = (79, 140, 255)
CURSOR = (240, 244, 252)
CURSOR_EDGE = (22, 27, 36)
ASSETS = Path(__file__).resolve().parent


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def gradient(size: int) -> Image.Image:
    base = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(base)
    for y in range(size):
        ratio = y / (size - 1)
        colour = tuple(round(a + (b - a) * ratio) for a, b in zip(BACKGROUND_TOP, BACKGROUND_BOTTOM))
        draw.line([(0, y), (size, y)], fill=colour + (255,))
    return base


def cursor_polygon(tip, scale: float):
    shape = [
        (0.0, 0.0),
        (0.0, 15.6),
        (3.8, 12.2),
        (6.6, 17.9),
        (9.2, 16.8),
        (6.3, 11.2),
        (11.7, 11.0),
    ]
    return [(tip[0] + x * scale, tip[1] + y * scale) for x, y in shape]


def ripple(draw: ImageDraw.ImageDraw, centre, radius, width, colour):
    bbox = [centre[0] - radius, centre[1] - radius, centre[0] + radius, centre[1] + radius]
    draw.arc(bbox, start=195, end=105, fill=colour, width=width)


def build() -> Image.Image:
    icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    icon.paste(gradient(SIZE), (0, 0), rounded_mask(SIZE, 54))
    frame = ImageDraw.Draw(icon)
    frame.rounded_rectangle([2, 2, SIZE - 3, SIZE - 3], radius=52, outline=BORDER + (150,), width=3)
    tip = (94, 82)
    ripple(frame, tip, 74, 8, ACCENT + (55,))
    ripple(frame, tip, 44, 10, ACCENT + (140,))
    ripple(frame, tip, 20, 9, ACCENT + (255,))
    frame.polygon(cursor_polygon(tip, 8.6), fill=CURSOR + (255,), outline=CURSOR_EDGE + (255,))
    ImageDraw.Draw(icon).polygon(cursor_polygon(tip, 8.6), outline=CURSOR + (70,), width=2)
    return icon


def main() -> None:
    icon = build()
    icon.save(ASSETS / "icon.png")
    icon.save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    preview = icon.resize((128, 128), Image.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
    canvas.alpha_composite(preview)
    canvas.convert("RGB").save(ASSETS / "icon-preview.png")


if __name__ == "__main__":
    main()
