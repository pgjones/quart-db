import asyncio
from sqlite3 import PARSE_COLNAMES, ProgrammingError
from types import TracebackType
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from urllib.parse import urlsplit
from uuid import uuid4

import aiosqlite

from ..interfaces import (
    BackendABC,
    ConnectionABC,
    RecordType,
    TransactionABC,
    TypeConverters,
    UndefinedParameterError,
)


class Transaction(TransactionABC):
    def __init__(self, connection: "Connection", *, force_rollback: bool = False) -> None:
        self._connection = connection
        self._force_rollback = force_rollback
        self._savepoints: List[str] = []

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
            savepoint_name = f"STARLETTE_SAVEPOINT_{uuid4().hex}"
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

    async def execute(self, query: str, values: Optional[Dict[str, Any]] = None) -> None:
        try:
            async with self._lock:
                await self._connection.execute(query, values)
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def execute_many(self, query: str, values: List[Dict[str, Any]]) -> None:
        if not values:
            return

        try:
            async with self._lock:
                await self._connection.executemany(query, values)
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_all(
        self,
        query: str,
        values: Optional[Dict[str, Any]] = None,
    ) -> List[RecordType]:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    rows = await cursor.fetchall()
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            return [{key: row[key] for key in row.keys()} for row in rows]

    async def fetch_one(
        self,
        query: str,
        values: Optional[Dict[str, Any]] = None,
    ) -> RecordType:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    row = await cursor.fetchone()
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            return {key: row[key] for key in row.keys()}

    async def fetch_val(
        self,
        query: str,
        values: Optional[Dict[str, Any]] = None,
    ) -> Any:
        try:
            async with self._lock:
                async with self._connection.execute(query, values) as cursor:
                    result = await cursor.fetchone()
        except ProgrammingError as error:
            raise UndefinedParameterError(str(error))
        else:
            return result[0]

    async def iterate(  # type: ignore[override]
        self,
        query: str,
        values: Optional[Dict[str, Any]] = None,
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
    def __init__(
        self,
        url: str,
        type_converters: TypeConverters,
    ) -> None:
        _, _, path, *_ = urlsplit(url)
        self._path = path[1:]
        self._connections: Set[aiosqlite.Connection] = set()
        for _, converters in type_converters.items():
            for typename, (encoder, decoder, pytype) in converters.items():
                aiosqlite.register_adapter(pytype, encoder)
                aiosqlite.register_converter(typename, decoder)

    async def connect(self) -> None:
        pass

    async def disconnect(self, timeout: Optional[int] = None) -> None:
        tasks = [asyncio.ensure_future(connection.close()) for connection in self._connections]
        await asyncio.wait_for(asyncio.gather(*tasks), timeout)

    async def acquire(self) -> Connection:
        connection = aiosqlite.connect(
            database=self._path,
            isolation_level=None,
            detect_types=PARSE_COLNAMES,
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
