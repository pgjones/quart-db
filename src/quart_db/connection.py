from types import TracebackType
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import asyncpg
from buildpg import BuildError, render

ValuesType = Union[Dict[str, Any], List[Any], None]


class UndefinedParameterError(Exception):
    pass


class Transaction:
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
        self._transaction = self._connection._connection.transaction()
        await self._transaction.start()

    async def commit(self) -> None:
        await self._transaction.commit()
        self._transaction = None

    async def rollback(self) -> None:
        await self._transaction.rollback()
        self._transaction = None


class Connection:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self._connection = connection

    async def execute(self, query: str, values: ValuesType = None) -> None:
        compiled_query, args = self._compile(query, values)
        try:
            return await self._connection.execute(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def execute_many(self, query: str, values: List[Dict[str, Any]]) -> None:
        if not values:
            return

        compiled_queries = [self._compile(query, value) for value in values]
        compiled_query = compiled_queries[0][0]
        args = [query[1] for query in compiled_queries]
        try:
            return await self._connection.executemany(compiled_query, args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_all(
        self,
        query: str,
        values: ValuesType = None,
    ) -> List[asyncpg.Record]:
        compiled_query, args = self._compile(query, values)
        try:
            return await self._connection.fetch(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_one(
        self,
        query: str,
        values: ValuesType = None,
    ) -> asyncpg.Record:
        compiled_query, args = self._compile(query, values)
        try:
            return await self._connection.fetchrow(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def fetch_val(
        self,
        query: str,
        values: ValuesType = None,
    ) -> Any:
        compiled_query, args = self._compile(query, values)
        try:
            return await self._connection.fetchval(compiled_query, *args)
        except asyncpg.exceptions.UndefinedParameterError as error:
            raise UndefinedParameterError(str(error))

    async def iterate(
        self,
        query: str,
        values: ValuesType = None,
    ) -> AsyncGenerator[asyncpg.Record, None]:
        compiled_query, args = self._compile(query, values)
        async with self._connection.transaction():
            try:
                async for record in self._connection.cursor(compiled_query, *args):
                    yield record
            except asyncpg.exceptions.UndefinedParameterError as error:
                raise UndefinedParameterError(str(error))

    def transaction(self, *, force_rollback: bool = False) -> "Transaction":
        return Transaction(self, force_rollback=force_rollback)

    def _compile(self, query: str, values: ValuesType = None) -> Tuple[str, List[Any]]:
        if isinstance(values, list):
            return query, []
        else:
            try:
                return render(query, **(values or {}))
            except BuildError as error:
                raise UndefinedParameterError(str(error))
