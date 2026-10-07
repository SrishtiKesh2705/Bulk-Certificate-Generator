from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def render_certificate_pdf(*, recipient_name, course_name, issued_by, issued_date) -> bytes:
    buf = BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(width, height))

    c.setLineWidth(3)
    c.rect(30, 30, width - 60, height - 60)

    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width / 2, height - 120, "Certificate of Completion")

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 190, "This is to certify that")

    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(width / 2, height - 245, recipient_name)

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 295, "has successfully completed")

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 335, course_name)

    c.setFont("Helvetica", 12)
    c.drawString(80, 90, f"Date: {issued_date:%d %B %Y}")
    if issued_by:
        c.drawRightString(width - 80, 90, f"Issued by: {issued_by}")

    c.showPage()
    c.save()
    return buf.getvalue()