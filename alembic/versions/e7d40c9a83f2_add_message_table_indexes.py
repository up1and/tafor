"""add message table indexes

Revision ID: e7d40c9a83f2
Revises: 1f6bc14c81fc
Create Date: 2026-08-25 15:20:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e7d40c9a83f2'
down_revision = 'b86e34a4f7f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_metars_created', 'metars', ['created'])
    op.create_index('ix_tafs_type_created', 'tafs', ['type', 'created'])
    op.create_index('ix_tafs_created', 'tafs', ['created'])
    op.create_index('ix_sigmets_type_created', 'sigmets', ['type', 'created'])


def downgrade():
    op.drop_index('ix_sigmets_type_created', table_name='sigmets')
    op.drop_index('ix_tafs_created', table_name='tafs')
    op.drop_index('ix_tafs_type_created', table_name='tafs')
    op.drop_index('ix_metars_created', table_name='metars')
