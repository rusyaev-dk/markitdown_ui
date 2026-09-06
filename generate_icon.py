"""Generates icon.ico for MarkItDown GUI: a document with a folded corner,
text lines, and a bold down-arrow morphing into an "M" accent — conveys
"document -> Markdown conversion".
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np

SIZE = 1024


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_gradient_bg(size, top, bottom):
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    for y in range(size):
        t = y / (size - 1)
        r, g, b = lerp_color(top, bottom, t)
        arr[y, :, 0] = r
        arr[y, :, 1] = g
        arr[y, :, 2] = b
    return Image.fromarray(arr, "RGB")


def rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def main():
    bg = make_gradient_bg(SIZE, (79, 70, 229), (6, 182, 212))  # indigo -> cyan
    mask = rounded_mask(SIZE, radius=int(SIZE * 0.22))
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(bg, (0, 0), mask)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # --- soft shadow behind the document ---
    doc_w, doc_h = int(SIZE * 0.46), int(SIZE * 0.60)
    doc_x = int(SIZE * 0.25)
    doc_y = int(SIZE * 0.19)
    fold = int(doc_w * 0.30)

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [doc_x + 18, doc_y + 26, doc_x + doc_w + 18, doc_y + doc_h + 26],
        radius=28, fill=(0, 0, 0, 90),
    )
    shadow = shadow.filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(24))
    canvas.alpha_composite(shadow)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # --- document body (white, rounded, folded top-right corner) ---
    doc_pts = [
        (doc_x, doc_y + 24),
        (doc_x, doc_y + doc_h),
        (doc_x, doc_y + doc_h),
    ]
    # Build the folded-corner document as a polygon with a rounded-rect base.
    doc = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dd = ImageDraw.Draw(doc)
    dd.rounded_rectangle([doc_x, doc_y, doc_x + doc_w, doc_y + doc_h], radius=26, fill=(255, 255, 255, 255))
    # cut the folded corner triangle then redraw as folded flap
    dd.polygon(
        [
            (doc_x + doc_w - fold, doc_y),
            (doc_x + doc_w, doc_y + fold),
            (doc_x + doc_w, doc_y),
        ],
        fill=(0, 0, 0, 0),
    )
    canvas.alpha_composite(doc)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # remove corner properly using mask compositing (simpler: draw white poly minus corner)
    # Redraw crisper: rectangle body + folded flap triangle in light gray
    draw.polygon(
        [
            (doc_x + doc_w - fold, doc_y),
            (doc_x + doc_w, doc_y + fold),
            (doc_x + doc_w - fold, doc_y + fold),
        ],
        fill=(210, 218, 230, 255),
    )
    draw.line(
        [(doc_x + doc_w - fold, doc_y), (doc_x + doc_w - fold, doc_y + fold), (doc_x + doc_w, doc_y + fold)],
        fill=(170, 180, 195, 255), width=6, joint="curve",
    )

    # --- text lines inside the document ---
    line_color = (183, 193, 210, 255)
    lx0 = doc_x + int(doc_w * 0.14)
    lx1 = doc_x + int(doc_w * 0.86)
    ly = doc_y + int(doc_h * 0.20)
    gap = int(doc_h * 0.085)
    widths = [1.0, 0.85, 0.92, 0.55]
    for i, w in enumerate(widths):
        y = ly + i * gap
        draw.rounded_rectangle([lx0, y, lx0 + (lx1 - lx0) * w, y + 18], radius=9, fill=line_color)

    # --- accent down-arrow / "convert" chevron near bottom, amber accent ---
    accent = (245, 158, 11, 255)  # amber
    ax = doc_x + doc_w // 2
    ay = doc_y + int(doc_h * 0.66)
    arrow_w = int(doc_w * 0.42)
    arrow_h = int(doc_h * 0.30)
    shaft_w = int(arrow_w * 0.34)
    draw.polygon(
        [
            (ax - shaft_w // 2, ay),
            (ax + shaft_w // 2, ay),
            (ax + shaft_w // 2, ay + arrow_h * 0.5),
            (ax + arrow_w // 2, ay + arrow_h * 0.5),
            (ax, ay + arrow_h),
            (ax - arrow_w // 2, ay + arrow_h * 0.5),
            (ax - shaft_w // 2, ay + arrow_h * 0.5),
        ],
        fill=accent,
    )

    # --- "MD" badge bottom-right, overlapping the document edge ---
    badge_r = int(SIZE * 0.145)
    bx = doc_x + doc_w - int(badge_r * 0.35)
    by = doc_y + doc_h - int(badge_r * 0.35)
    draw.ellipse([bx - badge_r, by - badge_r, bx + badge_r, by + badge_r], fill=(30, 41, 59, 255))
    draw.ellipse([bx - badge_r, by - badge_r, bx + badge_r, by + badge_r], outline=(255, 255, 255, 255), width=8)
    try:
        font = ImageFont.truetype("segoeuib.ttf", int(badge_r * 0.95))
    except OSError:
        font = ImageFont.load_default()
    text = "MD"
    tb = draw.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    draw.text((bx - tw / 2 - tb[0], by - th / 2 - tb[1]), text, font=font, fill=(255, 255, 255, 255))

    canvas.save("icon_preview.png")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    canvas.save("icon.ico", sizes=sizes)
    print("Saved icon.ico and icon_preview.png")


if __name__ == "__main__":
    main()
