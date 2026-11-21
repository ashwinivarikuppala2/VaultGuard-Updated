"""Module 3 - Threat Detection, Monitoring, Quarantine & Analytics Schema Migration

Revision ID: 0003_module3_threat_detection
Revises: 0002_module2_backup_engine
Create Date: 2026-11-05 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0003_threat'
down_revision: Union[str, None] = '0002_backup'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance detections table with threat intelligence columns
    op.add_column('detections', sa.Column('threat_name', sa.String(length=150), nullable=False, server_default='Ransomware.Generic.Heuristic'))
    op.add_column('detections', sa.Column('risk_score', sa.Float(), nullable=False, server_default='75.0'))
    op.add_column('detections', sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'))
    op.add_column('detections', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_detections_status', 'detections', ['status'], unique=False)

    # 2. Enhance quarantine_events table
    op.add_column('quarantine_events', sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=True))
    op.add_column('quarantine_events', sa.Column('file_path', sa.String(length=1024), nullable=True))
    op.add_column('quarantine_events', sa.Column('isolation_level', sa.String(length=50), nullable=False, server_default='ENDPOINT'))
    op.add_column('quarantine_events', sa.Column('quarantined_by_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('quarantine_events', sa.Column('restored_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quarantine_events', sa.Column('restored_by_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_quarantine_events_device_id', 'quarantine_events', ['device_id'], unique=False)

    # 3. Create detection_events table (raw telemetry stream)
    op.create_table(
        'detection_events',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('organization_id', sa.Uuid(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('detection_id', sa.Uuid(), sa.ForeignKey('detections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('rename_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('write_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('delete_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('entropy_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('extension_mismatch', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('canary_hit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('process_id', sa.Integer(), nullable=True),
        sa.Column('process_name', sa.String(length=255), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('raw_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_detection_events_id', 'detection_events', ['id'], unique=False)
    op.create_index('ix_detection_events_organization_id', 'detection_events', ['organization_id'], unique=False)
    op.create_index('ix_detection_events_device_id', 'detection_events', ['device_id'], unique=False)
    op.create_index('ix_detection_events_detection_id', 'detection_events', ['detection_id'], unique=False)
    op.create_index('ix_detection_events_event_type', 'detection_events', ['event_type'], unique=False)

    # 4. Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('organization_id', sa.Uuid(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='SET NULL'), nullable=True),
        sa.Column('detection_id', sa.Uuid(), sa.ForeignKey('detections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=2048), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NEW'),
        sa.Column('acknowledged_by_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mitigation_notes', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'], unique=False)
    op.create_index('ix_alerts_organization_id', 'alerts', ['organization_id'], unique=False)
    op.create_index('ix_alerts_device_id', 'alerts', ['device_id'], unique=False)
    op.create_index('ix_alerts_detection_id', 'alerts', ['detection_id'], unique=False)
    op.create_index('ix_alerts_severity', 'alerts', ['severity'], unique=False)
    op.create_index('ix_alerts_status', 'alerts', ['status'], unique=False)

    # 5. Create threat_rules table
    op.create_table(
        'threat_rules',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('organization_id', sa.Uuid(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('condition', sa.String(length=50), nullable=False, server_default='GREATER_THAN'),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False, server_default='20.0'),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='HIGH'),
        sa.Column('action', sa.String(length=50), nullable=False, server_default='ALERT'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_threat_rules_id', 'threat_rules', ['id'], unique=False)
    op.create_index('ix_threat_rules_organization_id', 'threat_rules', ['organization_id'], unique=False)
    op.create_index('ix_threat_rules_rule_type', 'threat_rules', ['rule_type'], unique=False)

    # 6. Create canary_files table
    op.create_table(
        'canary_files',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('organization_id', sa.Uuid(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('expected_hash_sha256', sa.String(length=64), nullable=False),
        sa.Column('canary_token', sa.String(length=128), nullable=False),
        sa.Column('is_tampered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tampered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_canary_files_id', 'canary_files', ['id'], unique=False)
    op.create_index('ix_canary_files_organization_id', 'canary_files', ['organization_id'], unique=False)
    op.create_index('ix_canary_files_device_id', 'canary_files', ['device_id'], unique=False)
    op.create_index('ix_canary_files_file_path', 'canary_files', ['file_path'], unique=False)
    op.create_index('ix_canary_files_is_tampered', 'canary_files', ['is_tampered'], unique=False)

    # 7. Create risk_scores table
    op.create_table(
        'risk_scores',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('organization_id', sa.Uuid(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.Uuid(), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('risk_level', sa.String(length=50), nullable=False, server_default='LOW'),
        sa.Column('factors', sa.JSON(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_risk_scores_id', 'risk_scores', ['id'], unique=False)
    op.create_index('ix_risk_scores_organization_id', 'risk_scores', ['organization_id'], unique=False)
    op.create_index('ix_risk_scores_device_id', 'risk_scores', ['device_id'], unique=False)
    op.create_index('ix_risk_scores_risk_level', 'risk_scores', ['risk_level'], unique=False)


def downgrade() -> None:
    op.drop_table('risk_scores')
    op.drop_table('canary_files')
    op.drop_table('threat_rules')
    op.drop_table('alerts')
    op.drop_table('detection_events')

    op.drop_index('ix_quarantine_events_device_id', table_name='quarantine_events')
    op.drop_column('quarantine_events', 'restored_by_id')
    op.drop_column('quarantine_events', 'restored_at')
    op.drop_column('quarantine_events', 'quarantined_by_id')
    op.drop_column('quarantine_events', 'isolation_level')
    op.drop_column('quarantine_events', 'file_path')
    op.drop_column('quarantine_events', 'device_id')

    op.drop_index('ix_detections_status', table_name='detections')
    op.drop_column('detections', 'resolved_at')
    op.drop_column('detections', 'status')
    op.drop_column('detections', 'risk_score')
    op.drop_column('detections', 'threat_name')

