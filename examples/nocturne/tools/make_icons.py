"""Generate every icon artefact from one 1024x1024 master.

    python tools/make_icons.py [master.png]

Outputs assets/logo.ico (Windows), assets/logo-<size>.png (Linux) and
assets/logo.iconset/ (run `iconutil -c icns` on macOS to finish the .icns).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZES = [16, 22, 24, 32, 48, 64, 128, 256, 512]
ICNS_SIZES = [16, 32, 128, 256, 512]


def placeholder_master() -> Image.Image:
    """A simple generated mark, so the build works with no artwork checked in."""
    image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([48, 48, 976, 976], radius=190,
                           fill=(46, 52, 64, 255), outline=(136, 192, 208, 255), width=40)
    draw.polygon([(360, 700), (512, 300), (664, 700)], fill=(136, 192, 208, 255))
    draw.ellipse([452, 620, 572, 740], fill=(46, 52, 64, 255))
    return image


def build(master_path: Path | None, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if master_path is not None and master_path.exists():
        master = Image.open(master_path).convert("RGBA")
        if master.size != (1024, 1024):
            master = master.resize((1024, 1024), Image.LANCZOS)
    else:
        master = placeholder_master()

    master.save(out / "logo.ico", format="ICO", sizes=[(s, s) for s in ICO_SIZES])
    master.save(out / "logo.png")
    for size in PNG_SIZES:
        master.resize((size, size), Image.LANCZOS).save(out / f"logo-{size}.png")

    iconset = out / "logo.iconset"
    iconset.mkdir(exist_ok=True)
    for size in ICNS_SIZES:
        master.resize((size, size), Image.LANCZOS).save(
            iconset / f"icon_{size}x{size}.png")
        master.resize((size * 2, size * 2), Image.LANCZOS).save(
            iconset / f"icon_{size}x{size}@2x.png")

    print(f"wrote {out / 'logo.ico'} ({(out / 'logo.ico').stat().st_size} bytes)")
    print(f"wrote {len(PNG_SIZES)} PNGs and {len(ICNS_SIZES) * 2} iconset images")
    print("macOS: iconutil -c icns assets/logo.iconset -o assets/logo.icns")


if __name__ == "__main__":
    master = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets/logo-master.png")
    build(master, Path("assets"))
