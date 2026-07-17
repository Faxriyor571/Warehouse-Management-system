"""add employee_role

Revision ID: 34d1c102390c
Revises: ee047f26f8a1
Create Date: 2026-07-16 20:10:56.919760+00:00

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34d1c102390c'
down_revision: str | None = 'ee047f26f8a1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'employee_role',
            sa.Enum('CASHIER', 'WAREHOUSE', 'ACCOUNTANT', name='employee_role'),
            nullable=True,
        ),
    )
    op.create_index(op.f('ix_users_employee_role'), 'users', ['employee_role'], unique=False)
    # Backfill: every existing SELLER predates this job-function split, so
    # they're all cashiers today (the only employee type that existed before).
    op.execute("UPDATE users SET employee_role = 'CASHIER' WHERE role = 'SELLER'")


def downgrade() -> None:
    op.drop_index(op.f('ix_users_employee_role'), table_name='users')
    op.drop_column('users', 'employee_role')
    op.execute("DROP TYPE IF EXISTS employee_role")
