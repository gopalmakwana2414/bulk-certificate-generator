import atexit
import os
import shutil
import tempfile
from pathlib import Path

# The app reads its settings when it is imported, so the test settings must be
# set BEFORE importing anything from app. This keeps the tests away from the
# real database and the real generated_certificates folder.
test_dir = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{(test_dir / 'test.db').as_posix()}"
os.environ["CERTIFICATES_DIR"] = str(test_dir / "certificates")
atexit.register(shutil.rmtree, test_dir, ignore_errors=True)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    # fresh empty tables for every test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def make_recipients(count):
    return [
        {"name": f"Person {number}", "certificate_id": f"CERT-{number:03d}"}
        for number in range(1, count + 1)
    ]
