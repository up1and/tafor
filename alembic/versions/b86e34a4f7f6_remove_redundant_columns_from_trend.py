"""remove redundant columns from trend table

Revision ID: b86e34a4f7f6
Revises: 5d79cb3d6019
Create Date: 2023-11-17 11:53:40.674672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b86e34a4f7f6'
down_revision = '5d79cb3d6019'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('trends', 'heading')


def downgrade():
    op.add_column('trends', sa.Column('heading', sa.String(length=36)))
