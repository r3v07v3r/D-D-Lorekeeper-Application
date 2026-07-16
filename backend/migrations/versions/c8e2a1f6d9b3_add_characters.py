"""add characters

Revision ID: c8e2a1f6d9b3
Revises: b3c1f9e2a4d7
Create Date: 2026-07-16 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e2a1f6d9b3'
down_revision: Union[str, Sequence[str], None] = 'b3c1f9e2a4d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds a persisted Character table - one row per user, populated by
    either manual entry or D&D Beyond sync (see app/models.py:Character).
    Previously, D&D Beyond data lived only in an in-memory dict
    (CharacterSyncState.characters) with nothing for manual entry to write
    to at all.
    """
    op.create_table(
        'characters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('race', sa.String(), nullable=False, server_default=''),
        sa.Column('classes', sa.JSON(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('proficiency_bonus', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('ability_scores', sa.JSON(), nullable=False),
        sa.Column('hp_current', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('hp_max', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('hp_temp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('armor_class', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('armor_class_is_estimate', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('passive_perception', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('passive_perception_is_estimate', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('currencies', sa.JSON(), nullable=False),
        sa.Column('inventory', sa.JSON(), nullable=False),
        sa.Column('spell_slots', sa.JSON(), nullable=False),
        sa.Column('known_spells', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('characters')
