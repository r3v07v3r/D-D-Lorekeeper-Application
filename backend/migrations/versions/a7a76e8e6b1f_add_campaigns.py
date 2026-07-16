"""add campaigns

Revision ID: a7a76e8e6b1f
Revises: 6f4769b09904
Create Date: 2026-07-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7a76e8e6b1f'
down_revision: Union[str, Sequence[str], None] = '6f4769b09904'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds a real Campaign entity, replacing session_logs.campaign_name (a
    free-text string with no other structure) with a campaign_id FK - one
    Campaign row is backfilled per distinct existing campaign_name so no
    session log loses its campaign association.
    """
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('session_logs') as batch_op:
        batch_op.add_column(sa.Column('campaign_id', sa.Integer(), nullable=True))

    conn = op.get_bind()
    campaigns_table = sa.table('campaigns', sa.column('id', sa.Integer()), sa.column('name', sa.String()))
    session_logs_table = sa.table(
        'session_logs',
        sa.column('id', sa.Integer()),
        sa.column('campaign_name', sa.String()),
        sa.column('campaign_id', sa.Integer()),
    )

    distinct_names = conn.execute(sa.select(session_logs_table.c.campaign_name).distinct()).fetchall()
    for (name,) in distinct_names:
        result = conn.execute(campaigns_table.insert().values(name=name))
        # .inserted_primary_key is unreliable for a plain Core insert against
        # a manually-declared sa.table() in this SQLite/batch-migration
        # context (returns an empty tuple) - .lastrowid is the DBAPI-level
        # value SQLite actually guarantees for a single-row insert.
        new_id = result.lastrowid
        conn.execute(
            session_logs_table.update()
            .where(session_logs_table.c.campaign_name == name)
            .values(campaign_id=new_id)
        )

    with op.batch_alter_table('session_logs') as batch_op:
        batch_op.alter_column('campaign_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_session_logs_campaign_id', 'campaigns', ['campaign_id'], ['id'])
        batch_op.drop_column('campaign_name')


def downgrade() -> None:
    """Restores campaign_name from the related Campaign.name, then drops the
    campaigns table and the FK column.
    """
    with op.batch_alter_table('session_logs') as batch_op:
        batch_op.add_column(sa.Column('campaign_name', sa.String(), nullable=True))

    conn = op.get_bind()
    campaigns_table = sa.table('campaigns', sa.column('id', sa.Integer()), sa.column('name', sa.String()))
    session_logs_table = sa.table(
        'session_logs',
        sa.column('id', sa.Integer()),
        sa.column('campaign_name', sa.String()),
        sa.column('campaign_id', sa.Integer()),
    )
    campaigns = conn.execute(sa.select(campaigns_table.c.id, campaigns_table.c.name)).fetchall()
    for campaign_id, name in campaigns:
        conn.execute(
            session_logs_table.update()
            .where(session_logs_table.c.campaign_id == campaign_id)
            .values(campaign_name=name)
        )

    with op.batch_alter_table('session_logs') as batch_op:
        batch_op.alter_column('campaign_name', existing_type=sa.String(), nullable=False)
        batch_op.drop_constraint('fk_session_logs_campaign_id', type_='foreignkey')
        batch_op.drop_column('campaign_id')

    op.drop_table('campaigns')
