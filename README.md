# Bulk Certificate Generator

A backend API that takes a list of recipients, generates a PDF certificate for each of them from one predefined template, and keeps track of the progress of the whole job.

The client sends all recipients in one request, gets a job ID back immediately, and can then check the job status and download the certificates while they are being generated.

## Features

- Create a bulk generation job with `POST /api/jobs/`
- Request validation (empty names, empty/too long certificate IDs, duplicate IDs, too many recipients)
- Certificates are generated in the background, so the request does not wait
- Job status and progress (`pending`, `processing`, `completed`, `completed_with_errors`, `failed`)
- Success and failure counts for every job
- A failed certificate never stops the rest of the job; its error message is saved
- List the certificates of a job and download any generated PDF
- Automated tests with pytest
- Swagger documentation at `/docs`

## Tech Stack

- Python 3
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic (comes with FastAPI)
- ReportLab (PDF generation)
- Pytest (with httpx, which FastAPI's test client needs)

## Project Structure

```text
bulk-certificate-generator/
├── app/
│   ├── main.py                  # creates the FastAPI app, tables, error handler
│   ├── config.py                # settings (database url, output folder, max recipients)
│   ├── database.py              # engine, session, Base, get_db dependency
│   ├── models/                  # SQLAlchemy tables: GenerationJob, Certificate
│   ├── schemas/                 # Pydantic models for requests and responses
│   ├── routes/
│   │   ├── jobs.py              # /api/jobs endpoints
│   │   └── certificates.py      # /api/certificates download endpoint
│   ├── services/
│   │   ├── job_service.py       # creating jobs, background processing, counters
│   │   └── certificate_service.py   # creates one PDF file
│   └── utils/
│       └── certificate_template.py  # how the certificate looks
├── generated_certificates/      # PDFs are saved here
├── tests/
├── requirements.txt
├── .env.example
└── run.py
```

## Setup

Python 3.10 or newer is recommended.

```bash
git clone <repository-url>
cd bulk-certificate-generator
python -m venv venv
```

Activate the virtual environment:

```bash
# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Running the application

```bash
uvicorn app.main:app --reload
```

(`python run.py` does the same thing.)

The API runs on http://127.0.0.1:8000 and the Swagger UI is at http://127.0.0.1:8000/docs.

The SQLite file `certificates.db` is created automatically in the project folder on the first start. No configuration is needed. If you want to change the defaults, see `.env.example`.

## API Endpoints

### Create a job

`POST /api/jobs/` returns `201`

Request:

```json
{
  "recipients": [
    { "name": "Rahul Sharma", "certificate_id": "CERT-001" },
    { "name": "Priya Patel", "certificate_id": "CERT-002" }
  ]
}
```

Response:

```json
{
  "id": 1,
  "status": "pending",
  "total_count": 2,
  "success_count": 0,
  "failure_count": 0,
  "progress": 0,
  "created_at": "2026-10-07T06:58:25",
  "completed_at": null
}
```

### Get job status

`GET /api/jobs/{job_id}`

```json
{
  "id": 1,
  "status": "processing",
  "total_count": 10,
  "success_count": 6,
  "failure_count": 1,
  "progress": 70,
  "created_at": "2026-10-07T06:58:25",
  "completed_at": null
}
```

`progress` is the percentage of certificates that are already processed (successful + failed) out of the total.

### List the certificates of a job

`GET /api/jobs/{job_id}/certificates`

```json
[
  {
    "id": 1,
    "job_id": 1,
    "certificate_id": "CERT-001",
    "recipient_name": "Rahul Sharma",
    "status": "generated",
    "file_name": "certificate_1.pdf",
    "error_message": null,
    "created_at": "2026-10-07T06:58:25"
  },
  {
    "id": 2,
    "job_id": 1,
    "certificate_id": "CERT-002",
    "recipient_name": "राहुल शर्मा",
    "status": "failed",
    "file_name": null,
    "error_message": "ValueError: Recipient name contains characters the certificate font cannot print",
    "created_at": "2026-10-07T06:58:25"
  }
]
```

### Download a certificate

`GET /api/certificates/{certificate_id}/download`

Returns the PDF file. Note that `certificate_id` in this URL is the `id` field from the list above (the database id), not the `CERT-001` style value, because the same `CERT-001` could be used again in a different job.

### Error responses

| Status | When |
|--------|------|
| 404 | Job or certificate does not exist, or the PDF file is missing from disk |
| 409 | Certificate exists but was not generated (it failed or is still pending) |
| 422 | The request body is invalid (FastAPI/Pydantic validation) |
| 500 | Unexpected server error, returns `{"detail": "Internal server error"}` without any stack trace |

All errors are JSON with a `detail` field.

## How Bulk Processing Works

```text
Request
  -> Pydantic validates the body
  -> Create job (status "pending") and store every recipient as a "pending" certificate
  -> Return the job to the client (201)
  -> Background task starts: job becomes "processing"
  -> For each certificate: generate PDF, save result, update counters, commit
  -> Job gets its final status and completed_at
```

The processing is done with FastAPI's `BackgroundTasks`. The route saves the job, schedules `process_job(job_id)` and returns. FastAPI runs the task after the response is sent. The client then polls `GET /api/jobs/{job_id}`.

The counters are committed to the database after every certificate. That is why the status endpoint shows the real progress while the job is running.

Final status of a job:

- all certificates generated -> `completed`
- some failed, some generated -> `completed_with_errors`
- all failed (or the job itself crashed) -> `failed`

## Failure Handling

Every certificate is processed inside its own `try/except` in `process_certificate()`. If generating a PDF raises any error, the certificate is marked `failed`, the error message is stored, `failure_count` is increased, and the loop moves on to the next certificate. Nothing is re-raised, so one bad certificate cannot stop the job.

A real example: the template uses the Helvetica font, which only supports Western European characters. A name written in Hindi would show up as black boxes in the PDF, so the template raises an error for such names and that certificate is marked as failed, while the others are generated.

There is a second, outer `try/except` around the whole job. It only catches problems that are not about one certificate (for example the database going away) and marks the job as `failed`.

## Database Design

**generation_jobs**: one row per bulk request

| Column | Notes |
|--------|-------|
| id | primary key |
| status | pending / processing / completed / completed_with_errors / failed |
| total_count, success_count, failure_count | counters |
| created_at, completed_at | timestamps, `completed_at` is empty until the job ends |

**certificates**: one row per recipient

| Column | Notes |
|--------|-------|
| id | primary key |
| job_id | foreign key to `generation_jobs.id` |
| recipient_name, certificate_id | what the client sent |
| status | pending / generated / failed |
| file_path | where the PDF is saved, empty if it failed |
| error_message | reason for the failure, empty otherwise |
| created_at | timestamp |

One job has many certificates (`GenerationJob.certificates` / `Certificate.job` in SQLAlchemy). There is also a unique constraint on (`job_id`, `certificate_id`).

`progress` is not stored. It is calculated from the counters whenever the job is read.

## Design Decisions

- **SQLite**: no installation needed, so whoever reviews the project can run it right away. Because SQLAlchemy is used, switching to another database mostly means changing `DATABASE_URL`.
- **FastAPI**: automatic validation through Pydantic and automatic Swagger docs.
- **BackgroundTasks instead of Celery/Redis**: the work only needs to run inside the same process, and the project should start with a single command. The downside is that if the server restarts in the middle of a job, that job stays in `processing` (see Future Improvements).
- **Local file storage**: simple and enough for this scope. The PDF files are named `certificate_<database id>.pdf` and not after the certificate ID, because the certificate ID comes from the user and could contain characters like `/` or `..`.
- **One predefined template**: the whole design is in `app/utils/certificate_template.py`. The texts and colors are constants at the top of that file, so changing the wording or the look is easy.
- **Duplicate certificate IDs**: if a request contains the same certificate ID twice, the whole request is rejected with a clear message. The same ID in two different jobs is allowed.
- **Limit of 500 recipients per request** (`MAX_RECIPIENTS`), to avoid very large requests.
- **Separate database session in the background task**: the request's session is closed once the request is done, so the task opens its own.

## Testing

```bash
pytest
```

The tests use a temporary database and a temporary output folder, so they don't touch your real data. They cover job creation, validation, PDF generation, status and progress, failures in the middle of a job, and certificate download.

`TestClient` waits for background tasks to finish before returning, so in the tests the job is already finished after the POST call.

You may see a deprecation warning about `httpx` from Starlette's test client when running the tests. It does not affect the results.

## Future Improvements

None of these are implemented.

- PostgreSQL instead of SQLite
- Object storage (for example S3) for the PDF files
- Celery with Redis for larger workloads, and so that jobs survive a server restart
- Authentication
- Multiple templates
- Email delivery of the certificates
- A Unicode font so names in Hindi and other scripts can be printed
- Database migrations with Alembic
