from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth

# Everything you would want to change in the design is at the top.
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

TITLE = "Certificate of Completion"
INTRO_TEXT = "This is to certify that"
BODY_TEXT = "has successfully completed the training program"
SIGNATURE_LABEL = "Authorized Signatory"

MAIN_COLOR = colors.HexColor("#1f3a5f")
TEXT_COLOR = colors.HexColor("#333333")

NAME_FONT = "Helvetica-Bold"
NAME_FONT_SIZE = 34
MAX_NAME_WIDTH = PAGE_WIDTH - 160


def fit_font_size(text, font_name, start_size, max_width):
    # long names would run off the page, so shrink the font until it fits
    size = start_size
    while size > 10 and stringWidth(text, font_name, size) > max_width:
        size -= 1
    return size


def check_text_is_printable(label, text):
    # Helvetica only has Western European characters. Anything else (Hindi,
    # Chinese, ...) would silently show up as black boxes in the PDF, so we
    # fail loudly instead of producing a broken certificate.
    try:
        text.encode("cp1252")
    except UnicodeEncodeError:
        raise ValueError(f"{label} contains characters the certificate font cannot print")


def draw_certificate(pdf, recipient_name, certificate_id, issue_date):
    check_text_is_printable("Recipient name", recipient_name)
    check_text_is_printable("Certificate ID", certificate_id)

    center_x = PAGE_WIDTH / 2

    # double border
    pdf.setStrokeColor(MAIN_COLOR)
    pdf.setLineWidth(4)
    pdf.rect(30, 30, PAGE_WIDTH - 60, PAGE_HEIGHT - 60)
    pdf.setLineWidth(1)
    pdf.rect(42, 42, PAGE_WIDTH - 84, PAGE_HEIGHT - 84)

    pdf.setFillColor(MAIN_COLOR)
    pdf.setFont("Helvetica-Bold", 38)
    pdf.drawCentredString(center_x, PAGE_HEIGHT - 130, TITLE)

    pdf.setFillColor(TEXT_COLOR)
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(center_x, PAGE_HEIGHT - 190, INTRO_TEXT)

    name_size = fit_font_size(recipient_name, NAME_FONT, NAME_FONT_SIZE, MAX_NAME_WIDTH)
    pdf.setFillColor(MAIN_COLOR)
    pdf.setFont(NAME_FONT, name_size)
    pdf.drawCentredString(center_x, PAGE_HEIGHT - 250, recipient_name)

    # line under the name
    name_width = stringWidth(recipient_name, NAME_FONT, name_size)
    pdf.setLineWidth(1)
    pdf.line(center_x - name_width / 2 - 20, PAGE_HEIGHT - 262,
             center_x + name_width / 2 + 20, PAGE_HEIGHT - 262)

    pdf.setFillColor(TEXT_COLOR)
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(center_x, PAGE_HEIGHT - 305, BODY_TEXT)

    # footer: date on the left, signature on the right, certificate id in the middle
    pdf.setFont("Helvetica", 12)
    pdf.drawString(90, 100, "Issued on: " + issue_date.strftime("%d %B %Y"))

    pdf.line(PAGE_WIDTH - 260, 100, PAGE_WIDTH - 90, 100)
    pdf.drawCentredString(PAGE_WIDTH - 175, 82, SIGNATURE_LABEL)

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(center_x, 60, "Certificate ID: " + certificate_id)
