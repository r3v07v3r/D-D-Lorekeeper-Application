"""add user usage stats

Revision ID: b3c1f9e2a4d7
Revises: a7a76e8e6b1f
Create Date: 2026-07-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c1f9e2a4d7'
down_revision: Union[str, Sequence[str], None] = 'a7a76e8e6b1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds User.total_seconds_active, checkpointed at logout (see
    app/routers/auth.py) to back the Home dashboard's real "time in
    Lorekeeper" stat - server_default=0 so existing rows backfill cleanly.
    """
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('total_seconds_active', sa.Integer(), server_default='0', nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('total_seconds_active')
