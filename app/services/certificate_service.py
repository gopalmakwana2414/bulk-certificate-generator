from datetime import date

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.config import CERTIFICATES_DIR
from app.utils.certificate_template import draw_certificate


def generate_certificate_pdf(db_id, recipient_name, certificate_id):
    """Creates one PDF and returns the path of the file."""
    CERTIFICATES_DIR.mkdir(parents=True, exist_ok=True)

    # The file is named after the database id. The certificate_id comes from
    # the user and could contain characters like "/" or "..", so it is not
    # safe to use in a file name.
    file_path = CERTIFICATES_DIR / f"certificate_{db_id}.pdf"

    try:
        pdf = canvas.Canvas(str(file_path), pagesize=landscape(A4))
        draw_certificate(pdf, recipient_name, certificate_id, date.today())
        pdf.save()
    except Exception:
        # don't leave a half written file behind
        if file_path.exists():
            file_path.unlink()
        raise

    return str(file_path)
