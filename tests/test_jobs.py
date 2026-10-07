import pytest

from app.config import MAX_RECIPIENTS
from app.database import SessionLocal
from app.models import GenerationJob
from app.schemas import RecipientIn
from app.services import certificate_service, job_service
from tests.conftest import make_recipients


def test_create_job_with_valid_recipients(client):
    response = client.post("/api/jobs/", json={"recipients": make_recipients(3)})

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["total_count"] == 3

    with SessionLocal() as db:
        job = db.get(GenerationJob, data["id"])
        assert job is not None
        assert len(job.certificates) == 3
        assert job.certificates[0].recipient_name == "Person 1"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"recipients": []},
        {"recipients": [{"name": "", "certificate_id": "CERT-1"}]},
        {"recipients": [{"name": "   ", "certificate_id": "CERT-1"}]},
        {"recipients": [{"name": "Rahul", "certificate_id": ""}]},
        {"recipients": [{"name": "Rahul", "certificate_id": "X" * 51}]},
        {"recipients": [{"name": "Rahul"}]},
        {"recipients": [{"name": "A", "certificate_id": "CERT-1"}, {"name": "B", "certificate_id": "CERT-1"}]},
        {"recipients": make_recipients(MAX_RECIPIENTS + 1)},
    ],
    ids=[
        "recipients missing",
        "empty list",
        "empty name",
        "blank name",
        "empty certificate id",
        "certificate id too long",
        "certificate id missing",
        "duplicate certificate ids",
        "too many recipients",
    ],
)
def test_invalid_requests_are_rejected(client, payload):
    response = client.post("/api/jobs/", json=payload)

    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(GenerationJob).count() == 0  # nothing was saved


def test_duplicate_error_names_the_duplicate_id(client):
    recipients = [
        {"name": "A", "certificate_id": "CERT-1"},
        {"name": "B", "certificate_id": "CERT-1"},
    ]
    response = client.post("/api/jobs/", json={"recipients": recipients})

    assert "CERT-1" in response.text


def test_finished_job_status(client):
    # TestClient waits for the background task, so the job is done when post returns
    job_id = client.post("/api/jobs/", json={"recipients": make_recipients(4)}).json()["id"]

    data = client.get(f"/api/jobs/{job_id}").json()

    assert data["status"] == "completed"
    assert data["total_count"] == 4
    assert data["success_count"] == 4
    assert data["failure_count"] == 0
    assert data["progress"] == 100
    assert data["completed_at"] is not None


def test_progress_is_updated_while_processing(monkeypatch):
    recipients = [RecipientIn(**item) for item in make_recipients(4)]
    with SessionLocal() as db:
        job_id = job_service.create_job(db, recipients).id

    # each time a certificate is about to be generated, look at the job from
    # a separate session, like the status endpoint would
    snapshots = []
    real_generate = certificate_service.generate_certificate_pdf

    def spy(*args):
        with SessionLocal() as db:
            job = db.get(GenerationJob, job_id)
            snapshots.append((job.status, job.progress))
        return real_generate(*args)

    monkeypatch.setattr(certificate_service, "generate_certificate_pdf", spy)

    job_service.process_job(job_id)

    assert snapshots == [("processing", 0), ("processing", 25), ("processing", 50), ("processing", 75)]
    with SessionLocal() as db:
        job = db.get(GenerationJob, job_id)
        assert job.status == "completed"
        assert job.progress == 100


def test_unknown_job_returns_404(client):
    assert client.get("/api/jobs/999").status_code == 404
    assert client.get("/api/jobs/999/certificates").status_code == 404
