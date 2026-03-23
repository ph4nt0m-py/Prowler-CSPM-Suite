"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-03-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    user_role = postgresql.ENUM("admin", "user", name="user_role", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clients_tenant_id", "clients", ["tenant_id"])

    cred_provider = postgresql.ENUM("aws", "azure", "gcp", name="credential_provider", create_type=False)
    cred_auth = postgresql.ENUM("static_keys", "assume_role", name="credential_auth_method", create_type=False)
    cred_provider.create(op.get_bind(), checkfirst=True)
    cred_auth.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", cred_provider, nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("auth_method", cred_auth, nullable=False),
        sa.Column("ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("encryption_key_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_credentials_client_id", "credentials", ["client_id"])

    scan_status = postgresql.ENUM("pending", "running", "completed", "failed", name="scan_status", create_type=False)
    scan_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("credentials.id"), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("status", scan_status, nullable=False),
        sa.Column("progress_pct", sa.Integer, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("prowler_version", sa.String(64), nullable=True),
        sa.Column("output_directory", sa.String(1024), nullable=True),
        sa.Column("logs", sa.Text, nullable=True),
        sa.Column("previous_scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scans_client_id", "scans", ["client_id"])
    op.create_index("ix_scans_credential_id", "scans", ["credential_id"])

    finding_sev = postgresql.ENUM("low", "medium", "high", "critical", name="finding_severity", create_type=False)
    finding_stat = postgresql.ENUM("open", "closed", "new", name="finding_status", create_type=False)
    finding_sev.create(op.get_bind(), checkfirst=True)
    finding_stat.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("check_id", sa.String(512), nullable=False),
        sa.Column("resource_id", sa.Text, nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("service", sa.String(255), nullable=False),
        sa.Column("severity", finding_sev, nullable=False),
        sa.Column("status", finding_stat, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("compliance_framework", sa.String(255), nullable=True),
        sa.Column("raw_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scan_id", "fingerprint", name="uq_findings_scan_fingerprint"),
    )
    op.create_index("ix_findings_scan_id", "findings", ["scan_id"])
    op.create_index("ix_findings_fingerprint", "findings", ["fingerprint"])

    diff_cat = postgresql.ENUM("closed", "open", "new", name="diff_category", create_type=False)
    diff_cat.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "scan_diffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scan_diffs_scan_id", "scan_diffs", ["scan_id"])

    op.create_table(
        "scan_diff_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_diff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_diffs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("category", diff_cat, nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("findings.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_scan_diff_items_scan_diff_id", "scan_diff_items", ["scan_diff_id"])
    op.create_index("ix_scan_diff_items_fingerprint", "scan_diff_items", ["fingerprint"])

    triage_state = postgresql.ENUM("valid", "false_positive", "not_applicable", name="triage_state", create_type=False)
    triage_state.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "finding_triage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("state", triage_state, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", "fingerprint", name="uq_triage_client_fingerprint"),
    )
    op.create_index("ix_finding_triage_client_id", "finding_triage", ["client_id"])
    op.create_index("ix_finding_triage_fingerprint", "finding_triage", ["fingerprint"])


def downgrade() -> None:
    op.drop_table("finding_triage")
    op.drop_table("scan_diff_items")
    op.drop_table("scan_diffs")
    op.drop_table("findings")
    op.drop_table("scans")
    op.drop_table("credentials")
    op.drop_table("clients")
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS triage_state")
    op.execute("DROP TYPE IF EXISTS diff_category")
    op.execute("DROP TYPE IF EXISTS finding_status")
    op.execute("DROP TYPE IF EXISTS finding_severity")
    op.execute("DROP TYPE IF EXISTS scan_status")
    op.execute("DROP TYPE IF EXISTS credential_auth_method")
    op.execute("DROP TYPE IF EXISTS credential_provider")
    op.execute("DROP TYPE IF EXISTS user_role")
