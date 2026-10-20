"""Create a local mixed-content PDF for Document AI processor experiments."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


OUTPUT_PATH = Path("output/sample_mixed_document.pdf")
PAGE_WIDTH, PAGE_HEIGHT = letter


def _font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_scanned_page(path: Path) -> None:
    image = Image.new("RGB", (1650, 2200), "#f8f7f2")
    draw = ImageDraw.Draw(image)
    title_font = _font(62)
    body_font = _font(38)
    small_font = _font(30)

    draw.text((145, 150), "Equipment Loan Review", fill="#202b39", font=title_font)
    draw.line((145, 245, 1500, 245), fill="#718096", width=4)

    paragraphs = (
        "This page is a scanned-style image embedded in a PDF.",
        "The words on this page are pixels, not selectable PDF text.",
        "Applicant: Jordan Lee",
        "Application reference: DEMO-2048",
        "Requested amount: 125,000 dollars",
        "Purpose: purchase of manufacturing equipment",
        "The document is fictional and contains no real customer data.",
    )
    y = 340
    for paragraph in paragraphs:
        draw.text((145, y), paragraph, fill="#26364a", font=body_font)
        y += 145

    draw.rectangle((145, 1510, 1495, 1800), outline="#8794a3", width=4)
    draw.text((185, 1570), "Review note", fill="#1e3a5f", font=small_font)
    draw.text(
        (185, 1640),
        "Verify collateral and insurance before approval.",
        fill="#26364a",
        font=body_font,
    )
    draw.text((145, 2010), "Sample scan fixture | Page 2", fill="#67758a", font=small_font)
    image.save(path, format="PNG", dpi=(200, 200))


def _draw_chart(pdf: canvas.Canvas) -> None:
    x0, y0 = 100, 250
    chart_width, chart_height = 390, 220
    values = (115, 145, 175, 205)
    labels = ("Q1", "Q2", "Q3", "Q4")
    max_value = 250

    pdf.setFont("Helvetica-Bold", 15)
    pdf.setFillColor(colors.HexColor("#203552"))
    pdf.drawString(x0, y0 + chart_height + 45, "Illustrative Equipment Value by Quarter")
    pdf.setStrokeColor(colors.HexColor("#8292a6"))
    pdf.setLineWidth(1)
    pdf.line(x0, y0, x0 + chart_width, y0)
    pdf.line(x0, y0, x0, y0 + chart_height)

    bar_width = 52
    gap = 40
    for index, (value, label) in enumerate(zip(values, labels)):
        x = x0 + 32 + index * (bar_width + gap)
        height = chart_height * value / max_value
        pdf.setFillColor(colors.HexColor("#3977c3"))
        pdf.rect(x, y0, bar_width, height, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor("#203552"))
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(x + bar_width / 2, y0 - 18, label)
        pdf.drawCentredString(x + bar_width / 2, y0 + height + 7, str(value))

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#596a80"))
    pdf.drawString(x0, y0 - 42, "Illustrative index only; not a valuation or credit decision.")


def _draw_form_page(pdf: canvas.Canvas) -> None:
    pdf.setFillColor(colors.HexColor("#172c49"))
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(72, PAGE_HEIGHT - 78, "Equipment Loan Application")
    pdf.setFillColor(colors.HexColor("#4f6075"))
    pdf.setFont("Helvetica", 10)
    pdf.drawString(72, PAGE_HEIGHT - 98, "Demonstration form for key-value extraction")

    fields = (
        ("Applicant name", "Taylor Example"),
        ("Application ID", "DEMO-7316"),
        ("Requested loan amount", "$84,500"),
        ("Loan term", "48 months"),
        ("Equipment type", "Packaging line"),
        ("Supplier", "Northstar Industrial Supply"),
        ("Contact email", "taylor@example.invalid"),
    )
    label_x, value_x = 82, 315
    row_top = PAGE_HEIGHT - 165
    row_height = 52

    for index, (label, value) in enumerate(fields):
        y = row_top - index * row_height
        pdf.setStrokeColor(colors.HexColor("#c8d3df"))
        pdf.setLineWidth(0.8)
        pdf.line(72, y - 20, PAGE_WIDTH - 72, y - 20)
        pdf.setFillColor(colors.HexColor("#34465c"))
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(label_x, y, label)
        pdf.setFillColor(colors.HexColor("#15283f"))
        pdf.setFont("Helvetica", 11)
        pdf.drawString(value_x, y, value)

    checkbox_y = row_top - len(fields) * row_height - 25
    pdf.setStrokeColor(colors.HexColor("#50647c"))
    pdf.rect(label_x, checkbox_y - 2, 13, 13, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#15283f"))
    pdf.setFont("Helvetica", 10)
    pdf.drawString(label_x + 22, checkbox_y, "Applicant has confirmed the information above")

    pdf.setFillColor(colors.HexColor("#6a788a"))
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(72, 62, "All names, identifiers, amounts, and contact details are fictional.")


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    scanned_image_path = OUTPUT_PATH.parent / "sample_scanned_page.png"
    _draw_scanned_page(scanned_image_path)

    pdf = canvas.Canvas(str(OUTPUT_PATH), pagesize=letter)
    pdf.setTitle("Document AI Mixed Content Sample")
    pdf.setAuthor("Local Document AI sample")

    pdf.setFillColor(colors.HexColor("#172c49"))
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(72, PAGE_HEIGHT - 82, "Document AI Mixed-Content Sample")
    pdf.setFillColor(colors.HexColor("#34465c"))
    pdf.setFont("Helvetica", 12)
    pdf.drawString(72, PAGE_HEIGHT - 112, "Page 1 contains selectable text and a vector figure.")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(72, PAGE_HEIGHT - 145, "This fixture is generated locally and contains only fictional data.")
    _draw_chart(pdf)
    pdf.showPage()

    pdf.drawImage(
        str(scanned_image_path),
        72,
        72,
        width=PAGE_WIDTH - 144,
        height=PAGE_HEIGHT - 144,
        preserveAspectRatio=True,
        anchor="c",
    )
    pdf.showPage()

    _draw_form_page(pdf)
    pdf.showPage()
    pdf.save()

    print(f"Created {OUTPUT_PATH}")
    print(f"Created {scanned_image_path}")
    print("The PDF contains 3 pages: selectable text/figure, rasterized text, and a key-value form.")


if __name__ == "__main__":
    main()