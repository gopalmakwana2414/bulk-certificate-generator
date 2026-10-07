import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (importing it registers the tables)
from app.database import Base, engine
from app.routes import certificates, jobs

logger = logging.getLogger(__name__)

# Creates the tables on startup if they don't exist yet.
# A bigger project would use migrations (Alembic) instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bulk Certificate Generator",
    description="Submit a list of recipients, get a job back, and download the generated PDF certificates.",
    version="1.0.0",
)

app.include_router(jobs.router)
app.include_router(certificates.router)


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    # log the details on the server, but don't show them to the client
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
