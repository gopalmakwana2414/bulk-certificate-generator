import os

from app.database import SessionLocal
from app.models import Certificate
from tests.conftest import make_recipients


def create_job_and_get_certificates(client, recipients):
    job_id = client.post("/api/jobs/", json={"recipients": recipients}).json()["id"]
    return client.get(f"/api/jobs/{job_id}/certificates").json()


def test_list_certificates_of_a_job(client):
    certificates = create_job_and_get_certificates(client, make_recipients(2))

    assert len(certificates) == 2
    first = certificates[0]
    assert first["certificate_id"] == "CERT-001"
    assert first["recipient_name"] == "Person 1"
    assert first["status"] == "generated"
    assert first["file_name"].endswith(".pdf")
    assert first["error_message"] is None


def test_download_generated_certificate(client):
    certificate = create_job_and_get_certificates(client, make_recipients(1))[0]

    response = client.get(f"/api/certificates/{certificate['id']}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "CERT-001.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_download_unknown_certificate_returns_404(client):
    response = client.get("/api/certificates/999/download")

    assert response.status_code == 404


def test_download_failed_certificate_returns_409(client):
    recipients = make_recipients(1)
    recipients[0]["name"] = "राहुल शर्मा"
    certificate = create_job_and_get_certificates(client, recipients)[0]
    assert certificate["status"] == "failed"

    response = client.get(f"/api/certificates/{certificate['id']}/download")

    assert response.status_code == 409
    assert "failed" in response.json()["detail"]


def test_download_returns_404_if_file_was_deleted(client):
    certificate = create_job_and_get_certificates(client, make_recipients(1))[0]
    with SessionLocal() as db:
        os.remove(db.get(Certificate, certificate["id"]).file_path)

    response = client.get(f"/api/certificates/{certificate['id']}/download")

    assert response.status_code == 404


def test_weird_certificate_id_is_safe_in_file_name(client):
    recipients = [{"name": "Rahul", "certificate_id": "../../evil/CERT 1"}]
    certificate = create_job_and_get_certificates(client, recipients)[0]

    response = client.get(f"/api/certificates/{certificate['id']}/download")

    assert response.status_code == 200
    assert "/" not in certificate["file_name"]
    assert ".._.._evil_CERT_1.pdf" in response.headers["content-disposition"]
