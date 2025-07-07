import asyncio
import json
from types import TracebackType
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import asyncpg
import psycopg
from buildpg import BuildError, render
from psycopg.adapt import Dumper, Loader
from psycopg.rows import dict_row
from psycopg.types import TypeInfo
from psycopg_pool import AsyncConnectionPool

from ..interfaces import (
    BackendABC,
    ConnectionABC,
    MultipleRowsError,
    RecordType,
    TransactionABC,
    TypeConverters,
    UndefinedParameterError,
    ValueType,
)

try:
    from typing import LiteralString
except ImportError:
    from typing_extensions import LiteralString

try:
    from warnings import deprecated
except ImportError:
    from typing_extensions import deprecated

DEFAULT_TYPE_CONVERTERS: TypeConverters = {
    "pg_catalog": {
        "json": (json.dumps, json.loads, dict),
        "jsonb": (json.dumps, json.loads, dict),
    }
}


class Transaction(TransactionABC):
    def __init__(self, connection: "Connection", *, force_rollback: bool = False) -> None:
        self._connection = connection
        self._transaction: Optional[psycopg.AsyncTransaction] = None
        self._force_rollback = force_rollback

    async def __aenter__(self) -> "Transaction":
        await self.start()
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        if self._force_rollback or exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    async def start(self) -> None:
        self._transaction = psycopg.AsyncTransaction(self._connection._connection)
        await self._connection._connection.wait(self._transaction._enter_gen())

    async def commit(self) -> None:
        await self._connection._connection.wait(self._transaction._exit_gen(None, None, None))
        self._transaction = None

    async def rollback(self) -> None:
        self._transaction.force_rollback = True
        await self._connection._connection.wait(self._transaction._exit_gen(None, None, None))
        self._transaction = None


class Connection(ConnectionABC):
    supports_for_update = True

    def __init__(self, connection: psycopg.AsyncConnection) -> None:
        self._connection = connection

    async def execute(self, query: LiteralString, values: Optional[ValueType] = None) -> None:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute(compiled_query, args)
        except psycopg.ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def execute_many(self, query: LiteralString, values: List[ValueType]) -> None:
        if not values:
            return

        compiled_queries = [self._compile(query, value) for value in values]
        compiled_query = compiled_queries[0][0]
        args = [query[1] for query in compiled_queries]
        try:
            async with self._connection.cursor() as cursor:
                return await cursor.executemany(compiled_query, args)
        except psycopg.ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_all(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> List[RecordType]:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute(compiled_query, args)
                return await cursor.fetchall()  # type: ignore
        except psycopg.ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_first(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> Optional[RecordType]:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute(compiled_query, args)
                return await cursor.fetchone()  # type: ignore
        except psycopg.ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    @deprecated("Use fetch_first instead")
    async def fetch_one(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> Optional[RecordType]:
        return await self.fetch_first(query, values)

    async def fetch_sole(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> Optional[RecordType]:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute(compiled_query, args)
                rows = await cursor.fetchmany(2)
        except psycopg.ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            if len(rows) > 1:
                raise MultipleRowsError()
            elif len(rows) == 1:
                return rows[0]  # type: ignore
            else:
                return None

    async def fetch_val(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> Optional[Any]:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute(compiled_query, args)
                result = await cursor.fetchone()
                if result is not None:
                    return next(iter(result.values()))  # type: ignore
                else:
                    return None
        except psycopg.ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def iterate(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> AsyncGenerator[RecordType, None]:
        compiled_query, args = self._compile(query, values)
        async with self._connection.cursor() as cursor:
            try:
                async for record in cursor.stream(compiled_query, *args):
                    yield record  # type: ignore
            except psycopg.ProgrammingError as error:
                raise UndefinedParameterError(str(error))

    def transaction(self, *, force_rollback: bool = False) -> "Transaction":
        return Transaction(self, force_rollback=force_rollback)

    def _compile(
        self, query: LiteralString, values: Optional[ValueType] = None
    ) -> Tuple[str, List[Any]]:
        if isinstance(values, list):
            return query, values
        else:
            try:
                return render(query, **(values or {}))
            except BuildError as error:
                raise UndefinedParameterError(str(error))


class Backend(BackendABC):
    def __init__(self, url: str, options: Dict[str, Any], type_converters: TypeConverters) -> None:
        self._pool: Optional[asyncpg.Pool] = None
        self._url = url
        self._options = options
        self._type_converters = {**DEFAULT_TYPE_CONVERTERS, **type_converters}

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = AsyncConnectionPool(
                self._url,
                kwargs={
                    "autocommit": True,
                    "cursor_factory": psycopg.AsyncRawCursor,
                    "row_factory": dict_row,
                },
                **self._options,
            )
            await self._pool.open()

    async def disconnect(self, timeout: Optional[int] = None) -> None:
        if self._pool is not None:
            await asyncio.wait_for(self._pool.close(), timeout)
        self._pool = None

    async def acquire(self) -> Connection:
        connection = await self._pool.getconn()
        await _init_connection(connection, self._type_converters)
        return Connection(connection)

    async def release(self, connection: Connection) -> None:  # type: ignore[override]
        await self._pool.putconn(connection._connection)

    async def _acquire_migration_connection(self) -> Connection:
        psycopg_connection = await psycopg.AsyncConnection.connect(
            self._url, autocommit=True, cursor_factory=psycopg.AsyncRawCursor, row_factory=dict_row
        )
        await _init_connection(psycopg_connection, DEFAULT_TYPE_CONVERTERS)  # type: ignore
        return Connection(psycopg_connection)

    async def _release_migration_connection(self, connection: Connection) -> None:  # type: ignore[override]  # noqa: E501
        await connection._connection.close()

    async def _init(self, connection: asyncpg.Connection) -> None:
        await _init_connection(connection, self._type_converters)


class TestingBackend(BackendABC):
    def __init__(self, url: str, options: Dict[str, Any], type_converters: TypeConverters) -> None:
        self._url = url
        self._options = options
        self._type_converters = {**DEFAULT_TYPE_CONVERTERS, **type_converters}

    async def connect(self) -> None:
        self._connection = Connection(
            await psycopg.AsyncConnection.connect(
                self._url,
                autocommit=True,
                cursor_factory=psycopg.AsyncRawCursor,
                row_factory=dict_row,  # type: ignore
            )
        )
        await _init_connection(self._connection._connection, self._type_converters)  # type: ignore

    async def disconnect(self, timeout: Optional[int] = None) -> None:
        await asyncio.wait_for(self._connection._connection.close(), timeout)

    async def acquire(self) -> Connection:
        return self._connection

    async def release(self, connection: Connection) -> None:  # type: ignore[override]
        pass

    async def _acquire_migration_connection(self) -> Connection:
        psycopg_connection = await psycopg.AsyncConnection.connect(
            self._url, autocommit=True, cursor_factory=psycopg.AsyncRawCursor, row_factory=dict_row
        )
        await _init_connection(psycopg_connection, DEFAULT_TYPE_CONVERTERS)  # type: ignore
        return Connection(psycopg_connection)

    async def _release_migration_connection(self, connection: Connection) -> None:  # type: ignore[override]  # noqa: E501
        await connection._connection.close()


async def _init_connection(connection: psycopg.Connection, type_converters: TypeConverters) -> None:
    for schema, converters in type_converters.items():
        for typename, (encoder, decoder, type_) in converters.items():
            psycopg_type = await TypeInfo.fetch(connection, typename)  # type: ignore
            psycopg_type.register(connection)

            class CustomLoader(Loader):
                def load(self, data: bytes, decoder=decoder) -> Any:  # type: ignore
                    return decoder(data.decode())

            class CustomDumper(Dumper):
                oid = psycopg_type.oid

                def dump(self, elem: Any, encoder=encoder) -> bytes:  # type: ignore
                    return encoder(elem).encode()

            connection.adapters.register_loader(psycopg_type.oid, CustomLoader)
            connection.adapters.register_dumper(type_, CustomDumper)
