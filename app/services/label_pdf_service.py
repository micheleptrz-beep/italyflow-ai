"""
ItalyFlow AI - Label PDF print-ready service. ASCII only.
Generates CMYK-friendly PDF with bleed marks.
Requires: pip install reportlab
"""
from __future__ import annotations

import base64
import io

from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm as MM
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black


class LabelPdfService:
    @staticmethod
    def render_pdf(
        width_mm: int,
        height_mm: int,
        bleed_mm: int,
        layers: list[dict],
        with_marks: bool = True,
    ) -> bytes:
        page_w = (width_mm + 2 * bleed_mm) * mm
        page_h = (height_mm + 2 * bleed_mm) * mm
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(page_w, page_h))

        # Origin shifted by bleed; PDF y axis is bottom-up
        ox = bleed_mm * mm
        oy = bleed_mm * mm

        for layer in layers:
            ltype = layer.get("type")
            x = ox + float(layer.get("x", 0)) * mm
            w = float(layer.get("w", 10)) * mm
            h = float(layer.get("h", 10)) * mm
            # Convert top-down y to bottom-up
            y = oy + (height_mm - float(layer.get("y", 0)) - float(layer.get("h", 10))) * mm

            if ltype == "text":
                color = layer.get("color", "#111111")
                c.setFillColor(HexColor(color))
                font_size = int(layer.get("size_pt", 10))
                c.setFont(layer.get("font", "Helvetica"), font_size)
                text = str(layer.get("text", ""))
                tx = c.beginText(x, y + h - font_size)
                for line in text.split("\n"):
                    tx.textLine(line)
                c.drawText(tx)
            elif ltype == "shape":
                c.setFillColor(HexColor(layer.get("fill", "#000000")))
                c.rect(x, y, w, h, stroke=0, fill=1)
            elif ltype == "image":
                src = layer.get("src_b64", "")
                if src.startswith("data:image"):
                    raw = base64.b64decode(src.split(",", 1)[1])
                    img_buf = io.BytesIO(raw)
                    c.drawImage(img_buf, x, y, w, h, preserveAspectRatio=True, mask="auto")
            elif ltype == "barcode":
                c.setFillColor(black)
                c.rect(x, y + 3 * mm, w, h - 3 * mm, stroke=0, fill=1)
                c.setFont("Helvetica", 7)
                c.drawString(x, y, str(layer.get("value", "")))

        if with_marks:
            _draw_bleed_marks(c, bleed_mm, width_mm, height_mm)

        c.showPage()
        c.save()
        return buf.getvalue()


def _draw_bleed_marks(c, bleed_mm: int, w_mm: int, h_mm: int) -> None:
    c.setStrokeColor(black)
    c.setLineWidth(0.25)
    L = 3 * MM
    b = bleed_mm * MM
    W = (w_mm + 2 * bleed_mm) * MM
    H = (h_mm + 2 * bleed_mm) * MM
    # 4 corners
    corners = [
        (b, b), (W - b, b), (b, H - b), (W - b, H - b),
    ]
    for (x, y) in corners:
        c.line(x - L, y, x - 0.5 * MM, y)
        c.line(x + 0.5 * MM, y, x + L, y)
        c.line(x, y - L, x, y - 0.5 * MM)
        c.line(x, y + 0.5 * MM, x, y + L)
