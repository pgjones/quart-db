from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, AsyncGenerator, Callable, Dict, List, Mapping, Optional, Tuple, Type

RecordType = Mapping[str, Any]
TypeConverters = Dict[str, Dict[str, Tuple[Callable, Callable, Optional[Type]]]]


class UndefinedParameterError(Exception):
    pass


class TransactionABC(ABC):
    @abstractmethod
    async def __aenter__(self) -> "TransactionABC":
        pass

    @abstractmethod
    async def __aexit__(self, exc_type: type, exc_value: BaseException, tb: TracebackType) -> None:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass


class ConnectionABC(ABC):
    @property
    @abstractmethod
    def supports_for_update(self) -> bool:
        pass

    @abstractmethod
    async def execute(self, query: str, values: Optional[Dict[str, Any]] = None) -> None:
        """Execute a query, with bind values if needed

        The query accepts named arguments i.e. `:name`in the query
        with values set being a dictionary.

        """
        pass

    @abstractmethod
    async def execute_many(self, query: str, values: List[Dict[str, Any]]) -> None:
        """Execute a query for each set of values

        The query accepts a list of named arguments i.e. `:name`in the
        query with values set being a list of dictionaries.

        """
        pass

    @abstractmethod
    async def fetch_all(
        self, query: str, values: Optional[Dict[str, Any]] = None
    ) -> List[RecordType]:
        """Execute a query, returning all the result rows

        The query accepts named arguments i.e. `:name`in the query
        with values set being a dictionary.

        """
        pass

    @abstractmethod
    async def fetch_one(
        self, query: str, values: Optional[Dict[str, Any]] = None
    ) -> Optional[RecordType]:
        """Execute a query, returning only the first result rows

        The query accepts named arguments i.e. `:name`in the query
        with values set being a dictionary.

        """
        pass

    @abstractmethod
    async def fetch_val(self, query: str, values: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query, returning only a value

        The query accepts named arguments i.e. `:name`in the query
        with values set being a dictionary.

        """
        pass

    @abstractmethod
    def iterate(
        self,
        query: str,
        values: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[RecordType, None]:
        """Execute a query, and iterate over the result rows

        The query accepts named arguments i.e. `:name`in the query
        with values set being a dictionary.

        """
        pass

    @abstractmethod
    def transaction(self, *, force_rollback: bool = False) -> "TransactionABC":
        """Open a transaction

        .. code-block:: python

            async with connection.transaction():
                await connection.execute("SELECT 1")

        Arguments:
            force_rollback: Force the transaction to rollback on completion.
        """
        pass


class BackendABC(ABC):
    @abstractmethod
    def __init__(
        self, url: str, options: Optional[Dict[str, Any]], type_converters: TypeConverters
    ) -> None:
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the database.

        This will establish a connection pool if the backend supports
        it.

        """
        pass

    @abstractmethod
    async def disconnect(self, timeout: Optional[int] = None) -> None:
        """Disconnect from the database.

        This will wait up to timeout for any active queries to
        complete.

        """
        pass

    @abstractmethod
    async def acquire(self) -> ConnectionABC:
        """Acquire a connection to the database.

        Don't forget to release it after usage,

        .. code-block::: python

            connection = await backend.acquire()
            await connection.execute("SELECT 1")
            await quart_db.release(connection)

        """
        pass

    @abstractmethod
    async def release(self, connection: ConnectionABC) -> None:
        """Release a connection to the database.

        This should be used with :meth:`acquire`,

        .. code-block::: python

            connection = await backend.acquire() await
            connection.execute("SELECT 1") await
            quart_db.release(connection)

        """
        pass

    @abstractmethod
    async def _acquire_migration_connection(self) -> ConnectionABC:
        pass

    @abstractmethod
    async def _release_migration_connection(self, connection: ConnectionABC) -> None:
        pass
