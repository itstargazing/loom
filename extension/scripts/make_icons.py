from pathlib import Path

from PIL import Image

src = Path(
    r"C:\Users\gbekt\.cursor\projects\c-Users-gbekt-loom\assets"
    r"\c__Users_gbekt_AppData_Roaming_Cursor_User_workspaceStorage_"
    r"01ace350273b4c21f7af87ae98d8b340_images_logody-093e7f16-3458-425c-92de-2f690d1b5044.png"
)
out_dir = Path(r"c:\Users\gbekt\loom\extension\icons")
master_path = out_dir / "loom-mascot.png"
preview_path = Path(
    r"C:\Users\gbekt\.cursor\projects\c-Users-gbekt-loom\assets\loom-mascot-processed.png"
)


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


stops = [
    (0.0, (255, 236, 90)),
    (0.35, (255, 190, 40)),
    (0.7, (255, 120, 40)),
    (1.0, (255, 70, 140)),
]


def gradient_color(t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return (lerp(c0[0], c1[0], u), lerp(c0[1], c1[1], u), lerp(c0[2], c1[2], u))
    return stops[-1][1]


img = Image.open(src).convert("RGBA")
pixels = img.load()
w, h = img.size

for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        if r < 28 and g < 28 and b < 28:
            pixels[x, y] = (0, 0, 0, 0)
            continue
        if r < 45 and g < 45 and b < 45 and (r + g + b) < 100:
            pixels[x, y] = (0, 0, 0, 0)

bbox = img.getbbox()
if not bbox:
    raise SystemExit("nothing left after bg remove")

pad = 8
left, top, right, bottom = bbox
left = max(0, left - pad)
top = max(0, top - pad)
right = min(w, right + pad)
bottom = min(h, bottom + pad)
img = img.crop((left, top, right, bottom))
w, h = img.size
pixels = img.load()

# Gradient the L·O·O·M lettering on the chin (yellow/gold pixels only).
y_text_start = int(h * 0.72)
for y in range(y_text_start, h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        if a < 40:
            continue
        if r > 160 and g > 90 and b < 140 and (r + g) > (b * 3.2) and g > r * 0.45:
            nr, ng, nb = gradient_color(x / max(1, w - 1))
            lum = (r + g + b) / (3 * 255)
            factor = 0.65 + 0.35 * lum
            pixels[x, y] = (
                min(255, int(nr * factor)),
                min(255, int(ng * factor)),
                min(255, int(nb * factor)),
                a,
            )

side = max(w, h)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(img, ((side - w) // 2, (side - h) // 2), img)

out_dir.mkdir(parents=True, exist_ok=True)
square.save(master_path, optimize=True)
square.save(preview_path, optimize=True)

for size in (16, 32, 48, 128):
    resized = square.resize((size, size), Image.Resampling.LANCZOS)
    path = out_dir / f"icon{size}.png"
    resized.save(path, optimize=True)
    print(f"wrote {path.name} ({path.stat().st_size} bytes)")

print(f"master={master_path} size={square.size}")
print(f"preview={preview_path}")
