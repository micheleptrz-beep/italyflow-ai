"""
ItalyFlow AI - Label rasterization service (PNG preview). ASCII only.
"""
from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont

MM_TO_INCH = 1.0 / 25.4


def _mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm * MM_TO_INCH * dpi))


def _font(size_pt: int, dpi: int) -> ImageFont.FreeTypeFont:
    px = int(round(size_pt * dpi / 72.0))
    try:
        return ImageFont.truetype("DejaVuSans.ttf", px)
    except Exception:
        return ImageFont.load_default()


class LabelRenderService:
    @staticmethod
    def render_png(width_mm: int, height_mm: int, dpi: int, layers: list[dict]) -> bytes:
        W = _mm_to_px(width_mm, dpi)
        H = _mm_to_px(height_mm, dpi)
        img = Image.new("RGB", (W, H), "#ffffff")
        draw = ImageDraw.Draw(img)
        for layer in layers:
            ltype = layer.get("type")
            x = _mm_to_px(layer.get("x", 0), dpi)
            y = _mm_to_px(layer.get("y", 0), dpi)
            w = _mm_to_px(layer.get("w", 10), dpi)
            h = _mm_to_px(layer.get("h", 10), dpi)
            if ltype == "text":
                font = _font(int(layer.get("size_pt", 10)), dpi)
                draw.multiline_text((x, y), str(layer.get("text", "")),
                                    fill=layer.get("color", "#111111"),
                                    font=font, spacing=2)
            elif ltype == "shape":
                draw.rectangle([x, y, x + w, y + h], fill=layer.get("fill", "#000000"))
            elif ltype == "image":
                src = layer.get("src_b64", "")
                if src.startswith("data:image"):
                    raw = base64.b64decode(src.split(",", 1)[1])
                    sub = Image.open(io.BytesIO(raw)).convert("RGBA").resize((w, h))
                    img.paste(sub, (x, y), sub)
            elif ltype == "barcode":
                # Minimal placeholder: black rectangle + value text
                draw.rectangle([x, y, x + w, y + h - _mm_to_px(3, dpi)], fill="#000000")
                font = _font(8, dpi)
                draw.text((x, y + h - _mm_to_px(3, dpi)), str(layer.get("value", "")),
                          fill="#000000", font=font)
        out = io.BytesIO()
        img.save(out, "PNG", optimize=True)
        return out.getvalue()
