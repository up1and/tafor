import os
import logging

from sqlalchemy import pool, create_engine

from alembic import context

from tafor.core.models import Base

# this is the Alembic Config object, which provides
# access to the values within pyproject.toml in use.
config = context.config

# migration progress on stderr, SQL echo stays silent.
logging.basicConfig(
    level='WARNING', format='%(levelname)-5.5s [%(name)s] %(message)s', datefmt='%H:%M:%S',
)
logging.getLogger('alembic').setLevel('INFO')

database_url = os.environ.get(
    'TAFOR_DB_URL',
    'sqlite:///' + os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tafor', 'db.sqlite3',
    ),
)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        render_as_batch=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        def process_revision_directives(context, revision, directives):
            # SQLite's PRAGMA-based reflection reports legacy columns as
            # nullable even when they are PRIMARY KEY or NOT NULL in the DDL,
            # so drop nullable-only diffs that are pure reflection noise.
            from alembic.operations import ops as alembic_ops

            def clean(batch_ops):
                kept = []
                for op in batch_ops:
                    if isinstance(op, alembic_ops.AlterColumnOp):
                        has_nullable_change = getattr(op, 'modify_nullable', None) is not None
                        has_type_change = bool(getattr(op, 'modify_type', None))
                        if has_nullable_change and not has_type_change:
                            continue
                    kept.append(op)
                batch_ops[:] = kept

            for directive in directives[0]._upgrade_ops:
                for op in directive.ops:
                    inner = getattr(op, 'ops', None)
                    if inner is not None:
                        clean(inner)

        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
