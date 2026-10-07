from pathlib import Path

from app.services import certificate_service
from tests.conftest import make_recipients


def test_certificate_pdf_is_generated():
    path = certificate_service.generate_certificate_pdf(1, "Rahul Sharma", "CERT-001")

    pdf_file = Path(path)
    assert pdf_file.exists()
    assert pdf_file.read_bytes().startswith(b"%PDF")


def test_name_with_unsupported_characters_fails_and_leaves_no_file():
    try:
        certificate_service.generate_certificate_pdf(2, "राहुल शर्मा", "CERT-002")
    except ValueError as error:
        assert "cannot print" in str(error)
    else:
        raise AssertionError("expected a ValueError")

    assert not (certificate_service.CERTIFICATES_DIR / "certificate_2.pdf").exists()


def test_one_failed_certificate_does_not_stop_the_others(client):
    # a real failure, no mocking: the Hindi name can't be drawn with the font
    recipients = make_recipients(5)
    recipients[1]["name"] = "राहुल शर्मा"
    recipients[3]["name"] = "名前"

    job_id = client.post("/api/jobs/", json={"recipients": recipients}).json()["id"]

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "completed_with_errors"
    assert job["total_count"] == 5
    assert job["success_count"] == 3
    assert job["failure_count"] == 2
    assert job["progress"] == 100

    certificates = client.get(f"/api/jobs/{job_id}/certificates").json()
    statuses = [item["status"] for item in certificates]
    assert statuses == ["generated", "failed", "generated", "failed", "generated"]

    failed = certificates[1]
    assert failed["error_message"]
    assert failed["file_name"] is None
    # the certificate AFTER the failed one was still generated
    assert certificates[2]["file_name"] is not None


def test_unexpected_error_in_one_certificate_does_not_stop_the_others(client, monkeypatch):
    real_generate = certificate_service.generate_certificate_pdf

    def flaky_generate(db_id, recipient_name, certificate_id):
        if certificate_id == "CERT-002":
            raise RuntimeError("disk is full")
        return real_generate(db_id, recipient_name, certificate_id)

    monkeypatch.setattr(certificate_service, "generate_certificate_pdf", flaky_generate)

    job_id = client.post("/api/jobs/", json={"recipients": make_recipients(3)}).json()["id"]

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "completed_with_errors"
    assert job["success_count"] == 2
    assert job["failure_count"] == 1

    certificates = client.get(f"/api/jobs/{job_id}/certificates").json()
    assert certificates[1]["status"] == "failed"
    assert "disk is full" in certificates[1]["error_message"]
    assert certificates[2]["status"] == "generated"


def test_job_is_failed_when_every_certificate_fails(client, monkeypatch):
    def always_fail(*args):
        raise RuntimeError("template broken")

    monkeypatch.setattr(certificate_service, "generate_certificate_pdf", always_fail)

    job_id = client.post("/api/jobs/", json={"recipients": make_recipients(2)}).json()["id"]

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert job["success_count"] == 0
    assert job["failure_count"] == 2
