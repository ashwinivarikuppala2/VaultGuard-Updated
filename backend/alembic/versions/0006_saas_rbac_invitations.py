"""SaaS Multi-Role and Invitation System Migration

Revision ID: 0006_saas_rbac_invitations
Revises: 0005_device_status_quarantined
Create Date: 2026-11-15 15:15:00.000000

"""
import secrets
import uuid
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0006_saas_rbac_invitations'
down_revision: Union[str, None] = '0005_device_status_quarantined'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def generate_code() -> str:
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    p1 = "".join(secrets.choice(alphabet) for _ in range(4))
    p2 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"VG-{p1}-{p2}"


def upgrade() -> None:
    # 1. Add invite_code to organizations
    op.add_column('organizations', sa.Column('invite_code', sa.String(length=32), nullable=True))
    op.create_index('ix_organizations_invite_code', 'organizations', ['invite_code'], unique=True)

    # 2. Backfill invite_code for existing organizations
    bind = op.get_bind()
    org_rows = bind.execute(sa.text("SELECT id FROM organizations WHERE invite_code IS NULL")).fetchall()
    for row in org_rows:
        code = generate_code()
        bind.execute(
            sa.text("UPDATE organizations SET invite_code = :code WHERE id = :id"),
            {"code": code, "id": row[0]},
        )

    # 3. Make organization_id nullable on personal user resource tables
    op.alter_column('devices', 'organization_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('protected_folders', 'organization_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('files', 'organization_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('backup_jobs', 'organization_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('recovery_jobs', 'organization_id', existing_type=sa.Uuid(), nullable=True)

    # 4. Seed new SaaS roles: ADMIN, EMPLOYEE, INDIVIDUAL
    for role_name, role_desc in [
        ("ADMIN", "Organization Administrator managing fleet backup and recovery"),
        ("EMPLOYEE", "Organization Employee managing personal assigned endpoint"),
        ("INDIVIDUAL", "Personal standalone user protecting personal device"),
    ]:
        existing = bind.execute(sa.text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}).scalar()
        if not existing:
            bind.execute(
                sa.text(
                    "INSERT INTO roles (id, name, description, created_at, updated_at) "
                    "VALUES (:id, :name, :description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": str(uuid.uuid4()), "name": role_name, "description": role_desc},
            )

    # 5. Migrate users currently assigned to deprecated roles to ADMIN
    admin_role_id = bind.execute(sa.text("SELECT id FROM roles WHERE name = 'ADMIN'")).scalar()
    if admin_role_id:
        bind.execute(
            sa.text(
                "UPDATE users SET role_id = :admin_id WHERE role_id IN "
                "(SELECT id FROM roles WHERE name IN ('SUPER_ADMIN', 'ORG_ADMIN'))"
            ),
            {"admin_id": admin_role_id},
        )


def downgrade() -> None:
    # 1. Reset organization_id to non-nullable (where applicable)
    op.alter_column('recovery_jobs', 'organization_id', existing_type=sa.Uuid(), nullable=False)
    op.alter_column('backup_jobs', 'organization_id', existing_type=sa.Uuid(), nullable=False)
    op.alter_column('files', 'organization_id', existing_type=sa.Uuid(), nullable=False)
    op.alter_column('protected_folders', 'organization_id', existing_type=sa.Uuid(), nullable=False)
    op.alter_column('devices', 'organization_id', existing_type=sa.Uuid(), nullable=False)

    # 2. Drop invite_code column and index
    op.drop_index('ix_organizations_invite_code', table_name='organizations')
    op.drop_column('organizations', 'invite_code')
