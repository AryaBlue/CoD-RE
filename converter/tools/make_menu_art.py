"""BO2 map-select artwork from a BO1 map's own menu images.

Large (2048 square): the BO1 loading screen, upscaled. Blur: the same, blurred (menu backdrop).
Blit (512 x 256, transparent): the BO1 lobby preview cropped to 2:1 with feathered edges, drawn over the globe.

usage: make_menu_art.py <loadscreen image> <preview image> <output folder>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def large(loadscreen: Image.Image) -> Image.Image:
    return loadscreen.convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS)


def blur(image: Image.Image) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(24))


def blit(preview: Image.Image) -> Image.Image:
    src = preview.convert("RGB")
    w, h = src.size
    crop_h = w // 2
    top = (h - crop_h) // 2
    picture = src.crop((0, top, w, top + crop_h)).resize((512, 256), Image.Resampling.LANCZOS)
    # rounded, feathered mask so the picture sits on the globe like the stock map pieces
    mask = Image.new("L", (512, 256), 0)
    ImageDraw.Draw(mask).rounded_rectangle((10, 10, 501, 245), radius=28, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(6))
    out = picture.convert("RGBA")
    out.putalpha(mask)
    return out


def main() -> None:
    loadscreen, preview, folder = Image.open(sys.argv[1]), Image.open(sys.argv[2]), Path(sys.argv[3])
    folder.mkdir(parents=True, exist_ok=True)
    big = large(loadscreen)
    big.save(folder / "large.png")
    blur(big).save(folder / "blur.png")
    blit(preview).save(folder / "blit.png")
    print(f"wrote {folder}\\large.png, blur.png, blit.png")


if __name__ == "__main__":
    main()
