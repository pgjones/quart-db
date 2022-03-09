import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple, Type, Union

import asyncpg
from quart import Quart

from ._migration import setup_schema
from .connection import Connection

ValuesType = Union[Dict[str, Any], List[Any], None]


class QuartDB:
    """A QuartDB database instance from which connections can be acquired.

    This can be used to initialise Quart-Schema documentation a given
    app, either directly,

    .. code-block:: python

        app = Quart(__name__)
        quart_db = QuartDB(app)

    or via the factory pattern,

    .. code-block:: python

        quart_db = QuartDB()

        def create_app():
            app = Quart(__name__)
            quart_db.init_app(app)
            return app

    It can then be used to establish connections to the database,

    .. code-block:: python

        async with quart_db.connection() as connection:
            await connection.execute("SELECT 1")

    Arguments:
        app: The app to associate this instance with, can be None if
             using the factory pattern.
        url: The URL to use to connect to the database, can be None
             and QUART_DB_DATABASE_URL used instead.
        migrations_folder: Location of migrations relative to the
             app's root path, defaults to "migrations".
        data_path: Location of any initial data relative to the apps'
             root path. Can be None.
    """

    connection_class: Type[Connection] = Connection

    def __init__(
        self,
        app: Optional[Quart] = None,
        *,
        url: Optional[str] = None,
        migrations_folder: Optional[str] = "migrations",
        data_path: Optional[str] = None,
    ) -> None:
        self._close_timeout = 5  # Seconds
        self._url = url
        self._pool: Optional[asyncpg.Pool] = None
        self._type_converters: Dict[str, Dict[str, Tuple[Callable, Callable]]] = defaultdict(
            dict,
            pg_catalog={
                "json": (json.dumps, json.loads),
                "jsonb": (json.dumps, json.loads),
            },
        )
        self._migrations_folder = migrations_folder
        self._data_path = data_path
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Quart) -> None:
        if self._url is None:
            self._url = app.config["QUART_DB_DATABASE_URL"]
        if self._migrations_folder is None:
            self._migrations_folder = app.config.get("QUART_DB_MIGRATIONS_FOLDER")
        if self._data_path is None:
            self._data_path = app.config.get("QUART_DB_DATA_PATH")
        self._root_path = app.root_path

        app.before_serving(self.before_serving)
        app.after_serving(self.after_serving)

    async def before_serving(self) -> None:
        if self._migrations_folder is not None or self._data_path is not None:
            await self.migrate()
        await self.connect()

    async def after_serving(self) -> None:
        await asyncio.wait_for(self._pool.close(), self._close_timeout)
        self._pool = None

    async def migrate(self) -> None:
        asyncpg_connection = await asyncpg.connect(dsn=self._url)
        await asyncpg_connection.set_type_codec(
            "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )
        await asyncpg_connection.set_type_codec(
            "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )
        connection = Connection(asyncpg_connection)

        migrations_folder = None
        if self._migrations_folder is not None:
            migrations_folder = self._root_path / self._migrations_folder
        data_path = None
        if self._data_path is not None:
            data_path = self._root_path / self._data_path
        await setup_schema(connection, migrations_folder, data_path)
        await asyncpg_connection.close()

    async def connect(self) -> None:
        async def init(connection: asyncpg.Connection) -> None:
            for schema, converters in self._type_converters.items():
                for typename, converter in converters.items():
                    await connection.set_type_codec(
                        typename,
                        encoder=converter[0],
                        decoder=converter[1],
                        schema=schema,
                    )

        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._url, init=init)

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Connection]:
        """Acquire a connection to the database.

        This should be used in an async with block as so,

        .. code-block:: python

            async with quart_db.connection() as connection:
                await connection.execute("SELECT 1")

        """
        conn = await self.acquire()
        yield conn
        await self.release(conn)

    async def acquire(self) -> "Connection":
        """Acquire a connection to the database.

        Don't forget to release it after usage,

        .. code-block::: python

            connection = await quart_db.acquire()
            await connection.execute("SELECT 1")
            await quart_db.release(connection)
        """
        connection = await self._pool.acquire()
        return self.connection_class(connection)

    async def release(self, connection: "Connection") -> None:
        """Release a connection to the database.

        This should be used with :meth:`acquire`,

        .. code-block::: python

            connection = await quart_db.acquire()
            await connection.execute("SELECT 1")
            await quart_db.release(connection)
        """
        await self._pool.release(connection._connection)

    def set_converter(
        self,
        typename: str,
        encoder: Callable,
        decoder: Callable,
        *,
        schema: str = "public",
    ) -> None:
        """Set the type converter

        This allows postgres and python types to be converted between
        one another.

        Arguments:
            typename: The postgres name for the type.
            encoder: A callable that takes the Python type and encodes it
                into data postgres understands.
            decoder: A callable that takes the postgres data and decodes
                it into a Python type.
            schema: Optional schema, defaults to "public".
        """
        self._type_converters[schema][typename] = (encoder, decoder)
