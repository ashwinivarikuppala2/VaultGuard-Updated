"""Ransomware Defense and Quarantine Tables

Revision ID: 0007_ransomware_protection_tables
Revises: 0006_saas_rbac_invitations
Create Date: 2026-11-16 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0007_ransomware_protection_tables'
down_revision: Union[str, None] = '0006_saas_rbac_invitations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ransomware_events
    op.create_table(
        'ransomware_events',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.Uuid(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='85.0'),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='HIGH'),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_ransomware_events_org', 'ransomware_events', ['organization_id'])
    op.create_index('ix_ransomware_events_device', 'ransomware_events', ['device_id'])
    op.create_index('ix_ransomware_events_user', 'ransomware_events', ['user_id'])
    op.create_index('ix_ransomware_events_status', 'ransomware_events', ['status'])

    # 2. Create quarantine_files
    op.create_table(
        'quarantine_files',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.Uuid(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('quarantine_path', sa.String(length=1024), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='QUARANTINED'),
        sa.Column('owner_name', sa.String(length=255), nullable=False, server_default='System User'),
        sa.Column('quarantined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('restored_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_quarantine_files_org', 'quarantine_files', ['organization_id'])
    op.create_index('ix_quarantine_files_device', 'quarantine_files', ['device_id'])
    op.create_index('ix_quarantine_files_status', 'quarantine_files', ['status'])

    # 3. Create scan_history
    op.create_table(
        'scan_history',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.Uuid(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=True),
        sa.Column('folder_path', sa.String(length=1024), nullable=False),
        sa.Column('files_scanned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('threats_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('threat_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('threat_level', sa.String(length=50), nullable=False, server_default='Safe'),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='COMPLETED'),
        sa.Column('scan_type', sa.String(length=50), nullable=False, server_default='REALTIME'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 4. Create threat_logs
    op.create_table(
        'threat_logs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.Uuid(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('device_id', sa.Uuid(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('threat_type', sa.String(length=100), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='HIGH'),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_threat_logs_org', 'threat_logs', ['organization_id'])
    op.create_index('ix_threat_logs_action', 'threat_logs', ['action'])
    op.create_index('ix_threat_logs_severity', 'threat_logs', ['severity'])


def downgrade() -> None:
    op.drop_table('threat_logs')
    op.drop_table('scan_history')
    op.drop_table('quarantine_files')
    op.drop_table('ransomware_events')
