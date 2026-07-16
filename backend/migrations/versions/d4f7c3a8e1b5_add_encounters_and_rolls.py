"""add encounters, combatants, roll log

Revision ID: d4f7c3a8e1b5
Revises: c8e2a1f6d9b3
Create Date: 2026-07-16 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f7c3a8e1b5'
down_revision: Union[str, Sequence[str], None] = 'c8e2a1f6d9b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds GM combat tracking (Encounter/Combatant) and a shared, polled
    roll log (RollLogEntry) - see app/models.py.
    """
    op.create_table(
        'encounters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, server_default='Encounter'),
        sa.Column('round', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('turn_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'combatants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('encounter_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('hp_current', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('hp_max', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('armor_class', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('initiative', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'roll_log_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('summary', sa.String(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('roll_log_entries')
    op.drop_table('combatants')
    op.drop_table('encounters')
