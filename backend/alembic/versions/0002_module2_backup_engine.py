"""Module 2 - Secure Backup Engine Schema Migration

Revision ID: 0002_module2_backup_engine
Revises: 0001_initial_schema
Create Date: 2026-11-05 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_backup'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. protected_folders table
    op.create_table(
        'protected_folders',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('organization_id', sa.Uuid(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('folder_path', sa.String(length=1024), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('scan_interval_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('include_patterns', sa.String(length=255), nullable=False, server_default='*.*'),
        sa.Column('exclude_patterns', sa.String(length=255), nullable=False, server_default='*.tmp,*.log,*.lock'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_protected_folders_id', 'protected_folders', ['id'], unique=False)
    op.create_index('ix_protected_folders_organization_id', 'protected_folders', ['organization_id'], unique=False)
    op.create_index('ix_protected_folders_device_id', 'protected_folders', ['device_id'], unique=False)

    # 2. Add columns to files
    op.add_column('files', sa.Column('protected_folder_id', sa.Uuid(), sa.ForeignKey('protected_folders.id', ondelete='SET NULL'), nullable=True))
    op.add_column('files', sa.Column('total_versions', sa.Integer(), nullable=False, server_default='1'))
    op.create_index('ix_files_protected_folder_id', 'files', ['protected_folder_id'], unique=False)

    # 3. Add columns to file_versions
    op.add_column('file_versions', sa.Column('original_size_bytes', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('file_versions', sa.Column('compressed_size_bytes', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('file_versions', sa.Column('compression_algorithm', sa.String(length=20), nullable=False, server_default='zlib'))
    op.add_column('file_versions', sa.Column('encryption_algorithm', sa.String(length=30), nullable=False, server_default='AES-256-GCM'))
    op.add_column('file_versions', sa.Column('nonce_hex', sa.String(length=64), nullable=True))
    op.add_column('file_versions', sa.Column('auth_tag_hex', sa.String(length=64), nullable=True))
    op.add_column('file_versions', sa.Column('is_encrypted', sa.Boolean(), nullable=False, server_default='true'))

    # 4. Add columns to backup_jobs
    op.add_column('backup_jobs', sa.Column('files_failed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('backup_jobs', sa.Column('files_skipped', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('backup_jobs', sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'))


def downgrade() -> None:
    op.drop_column('backup_jobs', 'duration_seconds')
    op.drop_column('backup_jobs', 'files_skipped')
    op.drop_column('backup_jobs', 'files_failed')

    op.drop_column('file_versions', 'is_encrypted')
    op.drop_column('file_versions', 'auth_tag_hex')
    op.drop_column('file_versions', 'nonce_hex')
    op.drop_column('file_versions', 'encryption_algorithm')
    op.drop_column('file_versions', 'compression_algorithm')
    op.drop_column('file_versions', 'compressed_size_bytes')
    op.drop_column('file_versions', 'original_size_bytes')

    op.drop_index('ix_files_protected_folder_id', table_name='files')
    op.drop_column('files', 'total_versions')
    op.drop_column('files', 'protected_folder_id')

    op.drop_index('ix_protected_folders_device_id', table_name='protected_folders')
    op.drop_index('ix_protected_folders_organization_id', table_name='protected_folders')
    op.drop_index('ix_protected_folders_id', table_name='protected_folders')
    op.drop_table('protected_folders')

