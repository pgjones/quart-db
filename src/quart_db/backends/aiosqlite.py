import asyncio
import json
from collections.abc import AsyncGenerator
from sqlite3 import PARSE_DECLTYPES, ProgrammingError
from types import TracebackType
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import aiosqlite

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
    "": {
        "json": (json.dumps, json.loads, dict),
    },
}


class Transaction(TransactionABC):
    def __init__(self, connection: "Connection", *, force_rollback: bool = False) -> None:
        self._connection = connection
        self._force_rollback = force_rollback
        self._savepoints: list[str] = []

    async def __aenter__(self) -> "Transaction":
        await self.start()
        return self

    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        if self._force_rollback or exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    async def start(self) -> None:
        if self._connection._connection.in_transaction:
            savepoint_name = f"QUART_DB_SAVEPOINT_{uuid4().hex}"
            await self._connection._connection.execute(f"SAVEPOINT {savepoint_name}")
            self._savepoints.append(savepoint_name)
        else:
            async with self._connection._lock:
                await self._connection._connection.execute("BEGIN")

    async def commit(self) -> None:
        if len(self._savepoints):
            savepoint_name = self._savepoints.pop()
            await self._connection._connection.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        else:
            async with self._connection._lock:
                await self._connection._connection.execute("COMMIT")

    async def rollback(self) -> None:
        if len(self._savepoints):
            savepoint_name = self._savepoints.pop()
            await self._connection._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        else:
            async with self._connection._lock:
                await self._connection._connection.execute("ROLLBACK")


class Connection(ConnectionABC):
    supports_for_update = False

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._connection = connection
        self._lock = asyncio.Lock()

    async def execute(self, query: LiteralString, values: ValueType | None = None) -> None:
        try:
            async with self._lock:
                await self._connection.execute(query, values)
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def execute_many(self, query: LiteralString, values: list[ValueType]) -> None:
        if not values:
            return

        try:
            async with self._lock:
                await self._connection.executemany(query, values)
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_all(
        self,
        query: LiteralString,
        values: ValueType | None = None,
    ) -> list[RecordType]:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    rows = await cursor.fetchall()
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            return [{key: row[key] for key in row.keys()} for row in rows]

    async def fetch_first(
        self,
        query: LiteralString,
        values: ValueType | None = None,
    ) -> RecordType | None:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    row = await cursor.fetchone()
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            if row is not None:
                return {key: row[key] for key in row.keys()}
            return None

    @deprecated("Use fetch_first instead")
    async def fetch_one(
        self,
        query: LiteralString,
        values: ValueType | None = None,
    ) -> RecordType | None:
        return await self.fetch_first(query, values)

    async def fetch_sole(
        self,
        query: LiteralString,
        values: ValueType | None = None,
    ) -> RecordType | None:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    rows = await cursor.fetchmany(2)
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            if len(rows) > 1:
                raise MultipleRowsError()
            elif len(rows) == 1:
                return {key: rows[0][key] for key in rows[0].keys()}
            else:
                return None

    async def fetch_val(
        self,
        query: LiteralString,
        values: ValueType | None = None,
    ) -> Any | None:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    result = await cursor.fetchone()
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            if result is not None:
                return result[0]
            return None

    async def iterate(
        self,
        query: LiteralString,
        values: ValueType | None = None,
    ) -> AsyncGenerator[RecordType, None]:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    async for row in cursor:
                        yield {key: row[key] for key in row.keys()}
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    def transaction(self, *, force_rollback: bool = False) -> "Transaction":
        return Transaction(self, force_rollback=force_rollback)


class Backend(BackendABC):
    def __init__(self, url: str, options: dict[str, Any], type_converters: TypeConverters) -> None:
        _, _, path, *_ = urlsplit(url)
        self._path = path[1:]
        self._options = options
        self._connections: set[aiosqlite.Connection] = set()
        for _, converters in {**DEFAULT_TYPE_CONVERTERS, **type_converters}.items():
            for typename, (encoder, decoder, pytype) in converters.items():
                aiosqlite.register_adapter(pytype, encoder)
                aiosqlite.register_converter(typename, decoder)

    async def connect(self) -> None:
        pass

    async def disconnect(self, timeout: int | None = None) -> None:
        tasks = [asyncio.ensure_future(connection.close()) for connection in self._connections]
        await asyncio.wait_for(asyncio.gather(*tasks), timeout)

    async def acquire(self) -> Connection:
        connection = aiosqlite.connect(
            database=self._path,
            isolation_level=None,
            detect_types=PARSE_DECLTYPES,
            **self._options,
        )
        await connection.__aenter__()
        connection.row_factory = aiosqlite.Row
        self._connections.add(connection)
        return Connection(connection)

    async def release(self, connection: Connection) -> None:  # type: ignore[override]
        await connection._connection.__aexit__(None, None, None)
        self._connections.remove(connection._connection)

    async def _acquire_migration_connection(self) -> Connection:
        connection = aiosqlite.connect(
            database=self._path,
            isolation_level=None,
        )
        await connection.__aenter__()
        connection.row_factory = aiosqlite.Row
        return Connection(connection)

    async def _release_migration_connection(self, connection: Connection) -> None:  # type: ignore[override]  # noqa: E501
        await connection._connection.__aexit__(None, None, None)


class TestingBackend(BackendABC):
    def __init__(self, url: str, options: dict[str, Any], type_converters: TypeConverters) -> None:
        _, _, path, *_ = urlsplit(url)
        self._path = path[1:]
        self._options = options
        for _, converters in {**DEFAULT_TYPE_CONVERTERS, **type_converters}.items():
            for typename, (encoder, decoder, pytype) in converters.items():
                aiosqlite.register_adapter(pytype, encoder)
                aiosqlite.register_converter(typename, decoder)

    async def connect(self) -> None:
        connection = aiosqlite.connect(
            database=self._path,
            isolation_level=None,
            detect_types=PARSE_DECLTYPES,
            **self._options,
        )
        await connection.__aenter__()
        self._connection = Connection(connection)

    async def disconnect(self, timeout: int | None = None) -> None:
        await asyncio.wait_for(self._connection._connection.close(), timeout)

    async def acquire(self) -> Connection:
        return self._connection

    async def release(self, connection: Connection) -> None:  # type: ignore[override]
        pass

    async def _acquire_migration_connection(self) -> Connection:
        connection = aiosqlite.connect(
            database=self._path,
            isolation_level=None,
        )
        await connection.__aenter__()
        connection.row_factory = aiosqlite.Row
        return Connection(connection)

    async def _release_migration_connection(self, connection: Connection) -> None:  # type: ignore[override]  # noqa: E501
        await connection._connection.__aexit__(None, None, None)
