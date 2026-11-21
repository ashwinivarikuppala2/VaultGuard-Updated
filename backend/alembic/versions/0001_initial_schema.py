"""Initial VaultGuard Database Schema Migration

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-04 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    # 2. organizations
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_devices', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('storage_quota_bytes', sa.BigInteger(), nullable=False, server_default='107374182400'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)
    op.create_index('ix_organizations_name', 'organizations', ['name'], unique=True)
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # 3. users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_organization_id', 'users', ['organization_id'], unique=False)
    op.create_index('ix_users_role_id', 'users', ['role_id'], unique=False)

    # 4. refresh_tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'], unique=False)
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'], unique=False)

    # 5. devices
    device_status_enum = sa.Enum('ONLINE', 'OFFLINE', 'REVOKED', 'PENDING', name='device_status_enum')
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('os', sa.String(length=100), nullable=False),
        sa.Column('status', device_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_devices_id', 'devices', ['id'], unique=False)
    op.create_index('ix_devices_device_id', 'devices', ['device_id'], unique=True)
    op.create_index('ix_devices_status', 'devices', ['status'], unique=False)
    op.create_index('ix_devices_organization_id', 'devices', ['organization_id'], unique=False)
    op.create_index('ix_devices_user_id', 'devices', ['user_id'], unique=False)

    # 6. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)

    # 7. files (placeholder)
    op.create_table(
        'files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_files_id', 'files', ['id'], unique=False)
    op.create_index('ix_files_organization_id', 'files', ['organization_id'], unique=False)
    op.create_index('ix_files_device_id', 'files', ['device_id'], unique=False)
    op.create_index('ix_files_file_path', 'files', ['file_path'], unique=False)

    # 8. file_versions (placeholder)
    op.create_table(
        'file_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('file_hash_sha256', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('entropy_score', sa.Float(), nullable=True),
        sa.Column('is_quarantined', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_file_versions_id', 'file_versions', ['id'], unique=False)
    op.create_index('ix_file_versions_file_id', 'file_versions', ['file_id'], unique=False)
    op.create_index('ix_file_versions_file_hash_sha256', 'file_versions', ['file_hash_sha256'], unique=False)

    # 9. backup_jobs (placeholder)
    op.create_table(
        'backup_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False, server_default='FULL'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_files', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bytes_processed', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_backup_jobs_id', 'backup_jobs', ['id'], unique=False)
    op.create_index('ix_backup_jobs_organization_id', 'backup_jobs', ['organization_id'], unique=False)
    op.create_index('ix_backup_jobs_device_id', 'backup_jobs', ['device_id'], unique=False)
    op.create_index('ix_backup_jobs_status', 'backup_jobs', ['status'], unique=False)

    # 10. detections (placeholder)
    op.create_table(
        'detections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('files.id', ondelete='SET NULL'), nullable=True),
        sa.Column('detection_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='HIGH'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_detections_id', 'detections', ['id'], unique=False)
    op.create_index('ix_detections_organization_id', 'detections', ['organization_id'], unique=False)
    op.create_index('ix_detections_device_id', 'detections', ['device_id'], unique=False)
    op.create_index('ix_detections_file_id', 'detections', ['file_id'], unique=False)
    op.create_index('ix_detections_severity', 'detections', ['severity'], unique=False)

    # 11. quarantine_events (placeholder)
    op.create_table(
        'quarantine_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('detection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('detections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('file_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('file_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_quarantine_events_id', 'quarantine_events', ['id'], unique=False)
    op.create_index('ix_quarantine_events_organization_id', 'quarantine_events', ['organization_id'], unique=False)
    op.create_index('ix_quarantine_events_detection_id', 'quarantine_events', ['detection_id'], unique=False)
    op.create_index('ix_quarantine_events_file_version_id', 'quarantine_events', ['file_version_id'], unique=False)

    # 12. recovery_jobs (placeholder)
    op.create_table(
        'recovery_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('files_restored', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_recovery_jobs_id', 'recovery_jobs', ['id'], unique=False)
    op.create_index('ix_recovery_jobs_organization_id', 'recovery_jobs', ['organization_id'], unique=False)
    op.create_index('ix_recovery_jobs_target_device_id', 'recovery_jobs', ['target_device_id'], unique=False)
    op.create_index('ix_recovery_jobs_status', 'recovery_jobs', ['status'], unique=False)

    # 13. approval_requests (placeholder)
    op.create_table(
        'approval_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('request_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_approval_requests_id', 'approval_requests', ['id'], unique=False)
    op.create_index('ix_approval_requests_organization_id', 'approval_requests', ['organization_id'], unique=False)
    op.create_index('ix_approval_requests_requested_by_id', 'approval_requests', ['requested_by_id'], unique=False)
    op.create_index('ix_approval_requests_approved_by_id', 'approval_requests', ['approved_by_id'], unique=False)
    op.create_index('ix_approval_requests_status', 'approval_requests', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('approval_requests')
    op.drop_table('recovery_jobs')
    op.drop_table('quarantine_events')
    op.drop_table('detections')
    op.drop_table('backup_jobs')
    op.drop_table('file_versions')
    op.drop_table('files')
    op.drop_table('audit_logs')
    op.drop_table('devices')
    op.execute('DROP TYPE device_status_enum')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
    op.drop_table('organizations')
    op.drop_table('roles')

