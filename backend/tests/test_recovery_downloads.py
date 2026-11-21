import io
import uuid
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import recovery
from app.models.recovery import RecoveryItemStatus, RecoveryJobStatus


@pytest.mark.asyncio
async def test_download_restored_item_returns_verified_payload(monkeypatch):
    item_id = uuid.uuid4()
    item = SimpleNamespace(
        id=item_id,
        status=RecoveryItemStatus.COMPLETED.value,
        sha256_verified=True,
        original_path=r"C:\Finance\quarterly.txt",
    )
    job = SimpleNamespace(
        id=uuid.uuid4(),
        status=RecoveryJobStatus.COMPLETED.value,
        items=[item],
    )
    monkeypatch.setattr(recovery, "_get_accessible_completed_job", AsyncMock(return_value=job))
    monkeypatch.setattr(
        recovery.recovery_service,
        "get_verified_item_payload",
        AsyncMock(return_value=b"verified contents"),
    )

    response = await recovery.download_restored_item(job.id, item_id, db=None, current_user=None)

    assert response.body == b"verified contents"
    assert response.media_type == "application/octet-stream"
    assert "quarterly.txt" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_download_recovery_archive_contains_verified_files(monkeypatch):
    item = SimpleNamespace(
        id=uuid.uuid4(),
        status=RecoveryItemStatus.COMPLETED.value,
        sha256_verified=True,
        original_path=r"C:\Finance\quarterly.txt",
    )
    job = SimpleNamespace(
        id=uuid.uuid4(),
        status=RecoveryJobStatus.COMPLETED.value,
        items=[item],
    )
    monkeypatch.setattr(recovery, "_get_accessible_completed_job", AsyncMock(return_value=job))
    monkeypatch.setattr(
        recovery.recovery_service,
        "get_verified_item_payload",
        AsyncMock(return_value=b"verified contents"),
    )

    response = await recovery.download_recovery_archive(job.id, db=None, current_user=None)
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    with zipfile.ZipFile(io.BytesIO(b"".join(chunks))) as archive:
        assert archive.namelist() == ["Finance/quarterly.txt"]
        assert archive.read("Finance/quarterly.txt") == b"verified contents"


@pytest.mark.asyncio
async def test_download_refuses_unverified_recovery_items(monkeypatch):
    item = SimpleNamespace(
        id=uuid.uuid4(),
        status=RecoveryItemStatus.FAILED.value,
        sha256_verified=False,
        original_path="quarterly.txt",
    )
    job = SimpleNamespace(
        id=uuid.uuid4(),
        status=RecoveryJobStatus.PARTIAL.value,
        items=[item],
    )
    monkeypatch.setattr(recovery, "_get_accessible_completed_job", AsyncMock(return_value=job))
    payload_loader = AsyncMock()
    monkeypatch.setattr(recovery.recovery_service, "get_verified_item_payload", payload_loader)

    with pytest.raises(HTTPException) as error:
        await recovery.download_restored_item(job.id, item.id, db=None, current_user=None)

    assert error.value.status_code == 404
    payload_loader.assert_not_awaited()
