from fastapi import FastAPI, BackgroundTasks
from starlette.responses import JSONResponse

from .database import engine
from .models import Base

app = FastAPI(title="Store Monitoring API")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def _run_ingestion_job() -> None:
    # Deferred absolute import to avoid heavy deps at import-time
    from scripts.ingest_data import ingest_data  # type: ignore
    ingest_data()


@app.post("/ingest")
def trigger_ingestion(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_ingestion_job)
    return JSONResponse({"message": "Ingestion started"})

