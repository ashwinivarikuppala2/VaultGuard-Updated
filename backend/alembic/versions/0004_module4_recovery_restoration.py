"""Module 4 - Recovery, Restoration, Integrity Verification & Recovery Operations Schema Migration

Revision ID: 0004_module4_recovery_restoration
Revises: 0003_module3_threat_detection
Create Date: 2026-11-05 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0004_recovery'
down_revision: Union[str, None] = '0003_threat'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance recovery_jobs table with restoration orchestrator attributes
    op.add_column('recovery_jobs', sa.Column('job_type', sa.String(length=50), nullable=False, server_default='SINGLE_FILE'))
    op.add_column('recovery_jobs', sa.Column('requested_by_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('recovery_jobs', sa.Column('destination_path', sa.String(length=1024), nullable=False, server_default='recovered_files'))
    op.add_column('recovery_jobs', sa.Column('destination_type', sa.String(length=50), nullable=False, server_default='SAFE_DIR'))
    op.add_column('recovery_jobs', sa.Column('overwrite_policy', sa.String(length=50), nullable=False, server_default='SKIP'))
    op.add_column('recovery_jobs', sa.Column('total_files', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('recovery_jobs', sa.Column('files_failed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('recovery_jobs', sa.Column('files_skipped', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('recovery_jobs', sa.Column('bytes_restored', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('recovery_jobs', sa.Column('error_message', sa.String(length=1024), nullable=True))
    op.add_column('recovery_jobs', sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('recovery_jobs', sa.Column('approval_request_id', sa.Uuid(), sa.ForeignKey('approval_requests.id', ondelete='SET NULL'), nullable=True))
    op.add_column('recovery_jobs', sa.Column('risk_assessment', sa.JSON(), nullable=True))

    op.alter_column('recovery_jobs', 'snapshot_time', existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column('recovery_jobs', 'target_device_id', existing_type=sa.Uuid(), nullable=True)

    op.create_index('ix_recovery_jobs_job_type', 'recovery_jobs', ['job_type'], unique=False)
    op.create_index('ix_recovery_jobs_requested_by_id', 'recovery_jobs', ['requested_by_id'], unique=False)
    op.create_index('ix_recovery_jobs_approval_request_id', 'recovery_jobs', ['approval_request_id'], unique=False)

    # 2. Create recovery_job_items table for granular item-level tracking
    op.create_table(
        'recovery_job_items',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('recovery_job_id', sa.Uuid(), sa.ForeignKey('recovery_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_id', sa.Uuid(), sa.ForeignKey('files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_version_id', sa.Uuid(), sa.ForeignKey('file_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_path', sa.String(length=1024), nullable=False),
        sa.Column('target_path', sa.String(length=1024), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('bytes_restored', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('sha256_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('threat_status', sa.String(length=50), nullable=False, server_default='no known threat detected'),
        sa.Column('threat_rationale', sa.String(length=1024), nullable=True),
        sa.Column('error_message', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_recovery_job_items_id', 'recovery_job_items', ['id'], unique=False)
    op.create_index('ix_recovery_job_items_recovery_job_id', 'recovery_job_items', ['recovery_job_id'], unique=False)
    op.create_index('ix_recovery_job_items_file_id', 'recovery_job_items', ['file_id'], unique=False)
    op.create_index('ix_recovery_job_items_file_version_id', 'recovery_job_items', ['file_version_id'], unique=False)
    op.create_index('ix_recovery_job_items_status', 'recovery_job_items', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('recovery_job_items')

    op.drop_index('ix_recovery_jobs_approval_request_id', table_name='recovery_jobs')
    op.drop_index('ix_recovery_jobs_requested_by_id', table_name='recovery_jobs')
    op.drop_index('ix_recovery_jobs_job_type', table_name='recovery_jobs')

    op.drop_column('recovery_jobs', 'risk_assessment')
    op.drop_column('recovery_jobs', 'approval_request_id')
    op.drop_column('recovery_jobs', 'requires_approval')
    op.drop_column('recovery_jobs', 'error_message')
    op.drop_column('recovery_jobs', 'bytes_restored')
    op.drop_column('recovery_jobs', 'files_skipped')
    op.drop_column('recovery_jobs', 'files_failed')
    op.drop_column('recovery_jobs', 'total_files')
    op.drop_column('recovery_jobs', 'overwrite_policy')
    op.drop_column('recovery_jobs', 'destination_type')
    op.drop_column('recovery_jobs', 'destination_path')
    op.drop_column('recovery_jobs', 'requested_by_id')
    op.drop_column('recovery_jobs', 'job_type')

