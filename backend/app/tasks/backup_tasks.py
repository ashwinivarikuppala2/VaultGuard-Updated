import asyncio
import os
import uuid
from typing import List, Optional
from app.tasks.celery_app import celery_app
from app.database.session import AsyncSessionLocal
from app.repositories.backup_repository import BackupRepository
from app.repositories.protected_folder_repository import ProtectedFolderRepository
from app.services.backup_service import BackupService


@celery_app.task(name="tasks.execute_folder_backup")
def execute_folder_backup(job_id_str: str, folder_id_str: str) -> dict:
    """Celery background worker task for scanning and backing up a protected folder."""
    return asyncio.run(_async_execute_folder_backup(uuid.UUID(job_id_str), uuid.UUID(folder_id_str)))


async def _async_execute_folder_backup(job_id: uuid.UUID, folder_id: uuid.UUID) -> dict:
    async with AsyncSessionLocal() as session:
        backup_repo = BackupRepository(session)
        folder_repo = ProtectedFolderRepository(session)
        backup_service = BackupService(session)

        job = await backup_repo.get_job_by_id(job_id)
        folder = await folder_repo.get_by_id(folder_id)

        if not job or not folder:
            return {"status": "FAILED", "reason": "Job or ProtectedFolder not found"}

        if not os.path.exists(folder.folder_path):
            await backup_repo.complete_job(
                job=job,
                status="FAILED",
                total_files=0,
                bytes_processed=0,
                files_failed=1,
                error_message=f"Directory path does not exist on device host: {folder.folder_path}",
            )
            await session.commit()
            return {"status": "FAILED", "error": "Folder not found"}

        total_files = 0
        bytes_processed = 0
        files_failed = 0
        files_skipped = 0

        for root, _, files in os.walk(folder.folder_path):
            for file_name in files:
                full_path = os.path.join(root, file_name)
                try:
                    with open(full_path, "rb") as f:
                        content = f.read()

                    await backup_service.process_file_backup(
                        organization_id=job.organization_id,
                        device_id=job.device_id,
                        file_path=full_path,
                        raw_bytes=content,
                        protected_folder_id=folder.id,
                        job_id=job.id,
                    )
                    total_files += 1
                    bytes_processed += len(content)
                except Exception as e:
                    files_failed += 1

        final_status = "COMPLETED" if files_failed == 0 else "PARTIAL"
        await backup_repo.complete_job(
            job=job,
            status=final_status,
            total_files=total_files,
            bytes_processed=bytes_processed,
            files_failed=files_failed,
            files_skipped=files_skipped,
        )
        await session.commit()

        return {
            "status": final_status,
            "total_files": total_files,
            "bytes_processed": bytes_processed,
            "files_failed": files_failed,
        }

