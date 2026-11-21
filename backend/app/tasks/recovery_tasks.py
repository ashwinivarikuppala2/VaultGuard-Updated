import asyncio
import logging
import uuid
from typing import Any, Dict

from app.database.session import AsyncSessionLocal
from app.services.recovery.recovery_service import recovery_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger("vaultguard.tasks.recovery")


@celery_app.task(name="tasks.execute_recovery_job")
def execute_recovery_task(job_id_str: str) -> Dict[str, Any]:
    """Celery background task for asynchronous recovery execution."""
    return asyncio.run(_async_run_recovery(uuid.UUID(job_id_str)))


async def _async_run_recovery(job_id: uuid.UUID) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        try:
            job = await recovery_service.execute_recovery_job(db=session, job_id=job_id)
            return {
                "job_id": str(job.id),
                "status": job.status,
                "files_restored": job.files_restored,
                "files_failed": job.files_failed,
                "files_skipped": job.files_skipped,
                "bytes_restored": job.bytes_restored,
            }
        except Exception as e:
            logger.error(f"Recovery task execution failed for job {job_id}: {str(e)}", exc_info=True)
            return {"job_id": str(job_id), "status": "FAILED", "error": str(e)}

