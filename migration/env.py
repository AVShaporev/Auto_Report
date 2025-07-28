import asyncio
from logging.config import fileConfig
import sys
from os.path import dirname, abspath

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from database.database import DATABASE_URL, Base
from model.role import Role
from model.user import User
from model.arial import Arial
from model.bank import Bank
from model.contract import Contract
from model.equipment import Equipment
from model.organization import Organization
from model.locality import Locality
from model.object import Object
from model.objects_equipment import Objects_Equipment
# from model.operation import Operation
from model.period import Period
from model.region import Region
from model.spec_arial import Spec_Arial
from model.spec_build import Spec_Build
from model.spec_contract import Spec_Contract
from model.spec_equipment import Spec_Equipment
from model.spec_job_title import Spec_Job_Title
from model.spec_locality import Spec_Locality
from model.spec_region import Spec_Region
from model.spec_room import Spec_Room
from model.spec_street import Spec_Street
from model.street import Street
from model.sub_contract import Sub_Contract
from model.report import Report
from model.spec_order import Spec_Order
from model.order import Order


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
