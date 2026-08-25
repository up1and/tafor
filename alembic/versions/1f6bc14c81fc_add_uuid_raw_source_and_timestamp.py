"""add uuid raw source and timestamp columns

Revision ID: 1f6bc14c81fc
Revises: b86e34a4f7f6
Create Date: 2026-08-24 19:08:18.698569

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f6bc14c81fc'
down_revision = '5d79cb3d6019'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite cannot ALTER COLUMN in place; batch mode recreates each table.
    # Only the columns missing from the 2023 migration chain are added here;
    # remaining type/nullable diffs reported by autogenerate are SQLite
    # reflection noise and are intentionally not touched.
    with op.batch_alter_table('metars', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('created', sa.DateTime(), nullable=True))
        batch_op.alter_column('type',
               existing_type=sa.Text(),
               type_=sa.String(length=2),
               existing_nullable=False)
        batch_op.alter_column('created',
               existing_type=sa.TEXT(),
               type_=sa.DateTime(),
               existing_nullable=True)

    with op.batch_alter_table('others', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('raw', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=16), nullable=True))
        batch_op.alter_column('protocol',
               existing_type=sa.VARCHAR(length=16),
               type_=sa.Text(),
               existing_nullable=True)
        batch_op.alter_column('created',
               existing_type=sa.TEXT(),
               type_=sa.DateTime(),
               existing_nullable=True)

    with op.batch_alter_table('sigmets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('raw', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('confirmed', sa.DateTime(), nullable=True))
        batch_op.alter_column('type',
               existing_type=sa.Text(),
               type_=sa.String(length=2),
               existing_nullable=False)
        batch_op.alter_column('heading',
               existing_type=sa.Text(),
               type_=sa.String(length=36),
               existing_nullable=True)
        batch_op.alter_column('protocol',
               existing_type=sa.VARCHAR(length=16),
               type_=sa.Text(),
               existing_nullable=True)
        batch_op.alter_column('created',
               existing_type=sa.TEXT(),
               type_=sa.DateTime(),
               existing_nullable=True)

    with op.batch_alter_table('tafs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('raw', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('confirmed', sa.DateTime(), nullable=True))
        batch_op.alter_column('type',
               existing_type=sa.Text(),
               type_=sa.String(length=2),
               existing_nullable=False)
        batch_op.alter_column('heading',
               existing_type=sa.Text(),
               type_=sa.String(length=36),
               existing_nullable=True)
        batch_op.alter_column('protocol',
               existing_type=sa.VARCHAR(length=16),
               type_=sa.Text(),
               existing_nullable=True)
        batch_op.alter_column('created',
               existing_type=sa.TEXT(),
               type_=sa.DateTime(),
               existing_nullable=True)

    with op.batch_alter_table('trends', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('raw', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=16), nullable=True))
        batch_op.alter_column('protocol',
               existing_type=sa.VARCHAR(length=16),
               type_=sa.Text(),
               existing_nullable=True)
        batch_op.alter_column('created',
               existing_type=sa.TEXT(),
               type_=sa.DateTime(),
               existing_nullable=True)


def downgrade():
    with op.batch_alter_table('trends', schema=None) as batch_op:
        batch_op.drop_column('source')
        batch_op.drop_column('raw')
        batch_op.drop_column('uuid')

    with op.batch_alter_table('tafs', schema=None) as batch_op:
        batch_op.drop_column('confirmed')
        batch_op.drop_column('source')
        batch_op.drop_column('raw')
        batch_op.drop_column('uuid')

    with op.batch_alter_table('sigmets', schema=None) as batch_op:
        batch_op.drop_column('confirmed')
        batch_op.drop_column('source')
        batch_op.drop_column('raw')
        batch_op.drop_column('uuid')

    with op.batch_alter_table('others', schema=None) as batch_op:
        batch_op.drop_column('source')
        batch_op.drop_column('raw')
        batch_op.drop_column('uuid')

    with op.batch_alter_table('metars', schema=None) as batch_op:
        batch_op.drop_column('created')
        batch_op.drop_column('uuid')
