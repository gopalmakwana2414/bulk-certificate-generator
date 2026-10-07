import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'certificates.db').as_posix()}"
)
CERTIFICATES_DIR = Path(
    os.getenv("CERTIFICATES_DIR", BASE_DIR / "generated_certificates")
)
MAX_RECIPIENTS = int(os.getenv("MAX_RECIPIENTS", "500"))
