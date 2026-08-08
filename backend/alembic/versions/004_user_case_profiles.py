"""Add user_case_profiles for Phase 5 case profile

Revision ID: 004
Revises: 003
Create Date: 2026-08-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_case_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("visa_type", sa.String(length=32), nullable=True),
        sa.Column("form_number", sa.String(length=32), nullable=True),
        sa.Column("service_center", sa.String(length=128), nullable=True),
        sa.Column("office_code", sa.String(length=64), nullable=True),
        sa.Column("priority_date", sa.String(length=32), nullable=True),
        sa.Column("country_of_chargeability", sa.String(length=128), nullable=True),
        sa.Column("has_dependents", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("premium_processing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("employer_name", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_case_profiles_user_id", "user_case_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_case_profiles_user_id", table_name="user_case_profiles")
    op.drop_table("user_case_profiles")
