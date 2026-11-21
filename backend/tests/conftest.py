import asyncio
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.session import Base, get_db
import app.models
from app.main import app
from app.models.role import Role, RoleType
from app.models.user import User
from app.security.password import hash_password

from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_vaultguard.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Bind test SQLite engine to app lifespan during tests
import app.main as main_module
main_module.engine = test_engine
main_module.AsyncSessionLocal = TestAsyncSessionLocal


@pytest.fixture
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed roles and super admin
    async with TestAsyncSessionLocal() as session:
        for r in RoleType:
            role = Role(name=r.value, description=f"Test {r.value}")
            session.add(role)
        await session.flush()

        from sqlalchemy import select
        res = await session.execute(select(Role).where(Role.name == RoleType.ADMIN.value))
        admin_role = res.scalar_one()

        admin_user = User(
            email="admin@vaultguard.internal",
            hashed_password=hash_password("AdminSecurePassword123!"),
            full_name="Test Administrator",
            role_id=admin_role.id,
            is_active=True,
            is_verified=True,
        )
        session.add(admin_user)
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from contextlib import asynccontextmanager

@asynccontextmanager
async def test_lifespan(app_instance):
    yield

app.router.lifespan_context = test_lifespan
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
async def client(setup_test_db) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

