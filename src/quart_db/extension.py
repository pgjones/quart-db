from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Optional, Type
from urllib.parse import urlsplit

import click
from quart import g, Quart, Response
from quart.cli import pass_script_info, ScriptInfo

from ._migration import setup_schema
from .interfaces import BackendABC, ConnectionABC, TypeConverters


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
        auto_request_connection: If True (the default) a connection
             is acquired and placed on g for each request.
    """

    def __init__(
        self,
        app: Optional[Quart] = None,
        *,
        url: Optional[str] = None,
        migrations_folder: Optional[str] = "migrations",
        data_path: Optional[str] = None,
        auto_request_connection: bool = True,
    ) -> None:
        self._close_timeout = 5  # Seconds
        self._url = url
        self._backend: Optional[BackendABC] = None
        self._type_converters: TypeConverters = defaultdict(dict)
        self._migrations_folder = migrations_folder
        self._data_path = data_path
        self._auto_request_connection = auto_request_connection
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
        self._testing = app.testing and app.config.get("QUART_DB_TESTING", None)

        if app.config["PROPAGATE_EXCEPTIONS"] is None:
            # Ensure exceptions aren't propagated so as to ensure
            # connections are released.
            app.config["PROPAGATE_EXCEPTIONS"] = False

        app.before_serving(self.before_serving)
        app.after_serving(self.after_serving)

        if app.config.get("QUART_DB_AUTO_REQUEST_CONNECTION", self._auto_request_connection):
            app.before_request(self.before_request)
            app.after_request(self.after_request)

        app.cli.add_command(_schema_command)

    async def before_serving(self) -> None:
        self._backend = self._create_backend()

        if self._migrations_folder is not None or self._data_path is not None:
            await self.migrate()
        await self._backend.connect()

    async def after_serving(self) -> None:
        await self._backend.disconnect(self._close_timeout)

    async def before_request(self) -> None:
        g.connection = await self.acquire()

    async def after_request(self, response: Response) -> Response:
        if getattr(g, "connection", None) is not None:
            await self.release(g.connection)
        g.connection = None
        return response

    async def migrate(self) -> None:
        connection = await self._backend._acquire_migration_connection()
        migrations_folder = None
        if self._migrations_folder is not None:
            migrations_folder = self._root_path / self._migrations_folder
        data_path = None
        if self._data_path is not None:
            data_path = self._root_path / self._data_path
        await setup_schema(connection, migrations_folder, data_path)
        await self._backend._release_migration_connection(connection)

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[ConnectionABC]:
        """Acquire a connection to the database.

        This should be used in an async with block as so,

        .. code-block:: python

            async with quart_db.connection() as connection:
                await connection.execute("SELECT 1")

        """
        conn = await self.acquire()
        yield conn
        await self.release(conn)

    async def acquire(self) -> ConnectionABC:
        """Acquire a connection to the database.

        Don't forget to release it after usage,

        .. code-block::: python

            connection = await quart_db.acquire()
            await connection.execute("SELECT 1")
            await quart_db.release(connection)
        """
        return await self._backend.acquire()

    async def release(self, connection: ConnectionABC) -> None:
        """Release a connection to the database.

        This should be used with :meth:`acquire`,

        .. code-block::: python

            connection = await quart_db.acquire()
            await connection.execute("SELECT 1")
            await quart_db.release(connection)
        """
        await self._backend.release(connection)

    def set_converter(
        self,
        typename: str,
        encoder: Callable,
        decoder: Callable,
        *,
        pytype: Optional[Type] = None,
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
            pytype: Optional Python type, required for SQLite.
            schema: Optional Postgres schema, defaults to "public".
        """
        self._type_converters[schema][typename] = (encoder, decoder, pytype)

    def _create_backend(self) -> BackendABC:
        scheme, *_ = urlsplit(self._url)
        if scheme in {"postgresql", "postgres"}:
            from .backends.asyncpg import Backend, TestingBackend

            if self._testing:
                return TestingBackend(self._url, self._type_converters)
            else:
                return Backend(self._url, self._type_converters)
        elif scheme == "sqlite":
            from .backends.aiosqlite import Backend, TestingBackend  # type: ignore

            if self._testing:
                return TestingBackend(self._url, self._type_converters)
            else:
                return Backend(self._url, self._type_converters)
        else:
            raise ValueError(f"{scheme} is not a supported backend")


@click.command("db-schema")
@click.option(
    "--output",
    "-o",
    default="quart_db_schema.png",
    type=click.Path(),
    help="Output the schema diagram to a file given by a path.",
)
@pass_script_info
def _schema_command(info: ScriptInfo, output: Optional[str]) -> None:
    app = info.load_app()

    try:
        from eralchemy2 import render_er  # type: ignore
    except ImportError:
        click.echo("Quart-DB needs to be installed with the erdiagram extra")
    else:
        render_er(app.config["QUART_DB_DATABASE_URL"], output, exclude_tables=["schema_migration"])
