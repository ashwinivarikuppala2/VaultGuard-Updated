import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, settings
from app.core.exceptions import StorageUnavailableException
from app.models.base import Base
from app.models.device import Device
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.storage.minio_client import minio_storage


def test_local_storage_defaults_off_in_production_and_on_for_local_development():
    assert Settings(
        ENVIRONMENT="production",
        SECRET_KEY="test-secret-key-that-is-long-enough",
    ).LOCAL_STORAGE_ENABLED is False
    assert Settings(ENVIRONMENT="development").LOCAL_STORAGE_ENABLED is True


def test_production_storage_fails_explicitly_when_minio_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_ENABLED", False)
    monkeypatch.setattr(minio_storage, "endpoint", "minio:9000")
    minio_storage.__dict__.pop("_available_cached", None)

    with pytest.raises(StorageUnavailableException):
        minio_storage.upload_bytes("demo/file.enc", b"encrypted")

    assert not (tmp_path / "vaultguard-storage" / "demo" / "file.enc").exists()


def test_explicit_local_demo_storage_round_trips_and_rejects_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LOCAL_STORAGE_ENABLED", True)
    monkeypatch.setattr(settings, "LOCAL_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(minio_storage, "endpoint", "minio:9000")
    minio_storage.__dict__.pop("_available_cached", None)

    object_key = "demo/file.enc"
    payload = b"encrypted demo content"
    minio_storage.upload_bytes(object_key, payload)

    assert minio_storage.download_bytes(object_key) == payload
    with pytest.raises(ValueError, match="Invalid local storage object path"):
        minio_storage.upload_bytes("../outside.enc", payload)
    assert not (tmp_path / "outside.enc").exists()


@pytest.mark.asyncio
async def test_startup_does_not_create_default_admin_or_placeholder_device(monkeypatch, tmp_path):
    from app import main

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'startup.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(main.settings, "FIRST_SUPER_ADMIN_PASSWORD", None)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        admin_role = Role(name="ADMIN", description="Test administrator")
        organization = Organization(
            name="Demo organization",
            slug="demo-organization",
            contact_email="admin@example.test",
        )
        session.add_all([admin_role, organization])
        await session.flush()
        session.add(
            User(
                email="real-admin@example.test",
                hashed_password="not-used",
                full_name="Real Admin",
                organization_id=organization.id,
                role_id=admin_role.id,
                is_active=True,
                is_verified=True,
            )
        )
        await session.commit()

    await main.init_system_defaults()

    async with session_factory() as session:
        seeded_admin = await session.scalar(
            select(User).where(User.email == main.settings.FIRST_SUPER_ADMIN_EMAIL)
        )
        device_count = await session.scalar(select(func.count(Device.id)))
        assert seeded_admin is None
        assert device_count == 0

    await engine.dispose()
