import asyncio
import json
from types import TracebackType
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import asyncpg
from buildpg import BuildError, render

from ..interfaces import (
    BackendABC,
    ConnectionABC,
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

DEFAULT_TYPE_CONVERTERS = {
    "pg_catalog": {
        "json": (json.dumps, json.loads, None),
        "jsonb": (json.dumps, json.loads, None),
    }
}


class Transaction(TransactionABC):
    def __init__(self, connection: "Connection", *, force_rollback: bool = False) -> None:
        self._connection = connection
        self._transaction: Optional[asyncpg.Transaction] = None
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
        async with self._connection._lock:
            self._transaction = self._connection._connection.transaction()
            await self._transaction.start()

    async def commit(self) -> None:
        async with self._connection._lock:
            await self._transaction.commit()
            self._transaction = None

    async def rollback(self) -> None:
        async with self._connection._lock:
            await self._transaction.rollback()
            self._transaction = None


class Connection(ConnectionABC):
    supports_for_update = True

    def __init__(self, connection: asyncpg.Connection) -> None:
        self._connection = connection
        self._lock = asyncio.Lock()

    async def execute(self, query: LiteralString, values: Optional[ValueType] = None) -> None:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._lock:
                return await self._connection.execute(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def execute_many(self, query: LiteralString, values: List[ValueType]) -> None:
        if not values:
            return

        compiled_queries = [self._compile(query, value) for value in values]
        compiled_query = compiled_queries[0][0]
        args = [query[1] for query in compiled_queries]
        try:
            async with self._lock:
                return await self._connection.executemany(compiled_query, args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_all(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> List[RecordType]:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._lock:
                return await self._connection.fetch(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_one(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> RecordType:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._lock:
                return await self._connection.fetchrow(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_val(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> Any:
        compiled_query, args = self._compile(query, values)
        try:
            async with self._lock:
                return await self._connection.fetchval(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def iterate(
        self,
        query: LiteralString,
        values: Optional[ValueType] = None,
    ) -> AsyncGenerator[RecordType, None]:
        compiled_query, args = self._compile(query, values)
        async with self._lock:
            async with self._connection.transaction():
                try:
                    async for record in self._connection.cursor(compiled_query, *args):
                        yield record
                except asyncpg.exceptions.UndefinedParameterError as error:
                    raise UndefinedParameterError(str(error))

    def transaction(self, *, force_rollback: bool = False) -> "Transaction":
        return Transaction(self, force_rollback=force_rollback)

    def _compile(
        self, query: LiteralString, values: Optional[ValueType] = None
    ) -> Tuple[str, List[Any]]:
        if isinstance(values, dict):
            try:
                return render(query, **(values or {}))
            except BuildError as error:
                raise UndefinedParameterError(str(error))
        elif values is not None:
            return query, values
        else:
            return query, []


class Backend(BackendABC):
    def __init__(self, url: str, options: Dict[str, Any], type_converters: TypeConverters) -> None:
        self._pool: Optional[asyncpg.Pool] = None
        self._url = url
        self._options = options
        self._type_converters = {**DEFAULT_TYPE_CONVERTERS, **type_converters}

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._url, init=self._init, **self._options)

    async def disconnect(self, timeout: Optional[int] = None) -> None:
        if self._pool is not None:
            await asyncio.wait_for(self._pool.close(), timeout)
        self._pool = None

    async def acquire(self) -> Connection:
        connection = await self._pool.acquire()
        return Connection(connection)

    async def release(self, connection: Connection) -> None:  # type: ignore[override]
        await self._pool.release(connection._connection)

    async def _acquire_migration_connection(self) -> Connection:
        asyncpg_connection = await asyncpg.connect(dsn=self._url)
        await _init_connection(asyncpg_connection, DEFAULT_TYPE_CONVERTERS)  # type: ignore
        return Connection(asyncpg_connection)

    async def _release_migration_connection(self, connection: Connection) -> None:  # type: ignore[override]  # noqa: E501
        await connection._connection.close()

    async def _init(self, connection: asyncpg.Connection) -> None:
        await _init_connection(connection, self._type_converters)  # type: ignore


class TestingBackend(BackendABC):
    def __init__(self, url: str, options: Dict[str, Any], type_converters: TypeConverters) -> None:
        self._url = url
        self._options = options
        self._type_converters = {**DEFAULT_TYPE_CONVERTERS, **type_converters}

    async def connect(self) -> None:
        self._connection = Connection(await asyncpg.connect(dsn=self._url, **self._options))
        await _init_connection(self._connection._connection, self._type_converters)  # type: ignore

    async def disconnect(self, timeout: Optional[int] = None) -> None:
        await asyncio.wait_for(self._connection._connection.close(), timeout)

    async def acquire(self) -> Connection:
        return self._connection

    async def release(self, connection: Connection) -> None:  # type: ignore[override]
        pass

    async def _acquire_migration_connection(self) -> Connection:
        asyncpg_connection = await asyncpg.connect(dsn=self._url)
        await _init_connection(asyncpg_connection, DEFAULT_TYPE_CONVERTERS)  # type: ignore
        return Connection(asyncpg_connection)

    async def _release_migration_connection(self, connection: Connection) -> None:  # type: ignore[override]  # noqa: E501
        await connection._connection.close()


async def _init_connection(connection: asyncpg.Connection, type_converters: TypeConverters) -> None:
    for schema, converters in type_converters.items():
        for typename, (encoder, decoder, _) in converters.items():
            await connection.set_type_codec(
                typename,
                encoder=encoder,
                decoder=decoder,
                schema=schema,
            )
