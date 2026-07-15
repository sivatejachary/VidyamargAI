import logging
from app.core.event_bus import event_bus
from app.job_discovery.workers.retry import WorkerRetryHandler
from app.services.vector_store import vector_store
from app.core.database import SessionLocal
from app.models.job_models import Job
from app.job_discovery.events.dispatcher import JobEventDispatcher

logger = logging.getLogger("app.job_discovery.workers.embedding.worker")

retry_handler = WorkerRetryHandler(max_retries=3)
dispatcher = JobEventDispatcher()

async def process_job_embedding(event: dict):
    """
    Core function to retrieve job, vector it using NVIDIA/Gemini API,
    and save it in Qdrant.
    """
    job_id = event.get("job_id")
    if not job_id:
        raise ValueError("Event is missing 'job_id'")

    logger.info(f"[Embedding Worker] Generating embedding for Job ID {job_id}")

    # 1. Fetch job details from Postgres
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job ID {job_id} not found in database")

        title = job.title
        company = job.company_name
        description = job.description
        skills = job.required_skills or []

        # 2. Vectorize and store in Qdrant
        if not vector_store.enabled:
            raise RuntimeError("Qdrant is disabled or unconfigured")

        success = await vector_store.upsert_job(
            job_id=job_id,
            title=title,
            company=company,
            description=description,
            skills=skills
        )

        if not success:
            raise RuntimeError(f"Upserting job ID {job_id} to Qdrant failed")

        # 3. Update PostgreSQL status
        job.lifecycle_status = "embedded"
        db.commit()

    # 4. Publish jobs.embedded.v1 event
    await dispatcher.publish_embedded(job_id)
    logger.info(f"[Embedding Worker] Successfully indexed and published jobs.embedded.v1 for Job ID {job_id}")


async def handle_job_persisted_event(event: dict):
    """
    Listens to jobs.persisted.v1 stream events and processes them with retry wrapper.
    """
    await retry_handler.execute_with_retry(
        stream="jobs.persisted.v1",
        event=event,
        handler_func=process_job_embedding
    )

async def start_embedding_worker():
    """Starts the embedding worker consumer subscription."""
    await event_bus.subscribe(
        stream="jobs.persisted.v1",
        handler=handle_job_persisted_event,
        group_name="embedding_workers_group",
        consumer_name="embedding_worker"
    )
    logger.info("[Embedding Worker] Registered subscriber for 'jobs.persisted.v1'.")
