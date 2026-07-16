"""add session highlights and recording window

Revision ID: e6a9b2d5f8c1
Revises: d4f7c3a8e1b5
Create Date: 2026-07-16 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6a9b2d5f8c1'
down_revision: Union[str, Sequence[str], None] = 'd4f7c3a8e1b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds SessionLog.highlights (LLM-extracted notable moments - see
    app/ai/pipeline.py) and recording_started_at/recording_ended_at, the
    real wall-clock window used to scope which roll-log entries belong to
    a given session (see app/bot/controller.py).
    """
    with op.batch_alter_table('session_logs') as batch_op:
        batch_op.add_column(sa.Column('highlights', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('recording_started_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('recording_ended_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('session_logs') as batch_op:
        batch_op.drop_column('recording_ended_at')
        batch_op.drop_column('recording_started_at')
        batch_op.drop_column('highlights')
