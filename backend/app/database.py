"""Database manager for BMKG Alert — async SQLite via aiosqlite."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import structlog

logger = structlog.get_logger()

_DB_INSTANCE: DatabaseManager | None = None


class DatabaseManager:
    """Manages async SQLite connection pool and schema initialization."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open database connection and enable WAL mode."""
        logger.info("database_connecting", path=self._db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        logger.info("database_connected", path=self._db_path)

    async def init_schema(self) -> None:
        """Execute schema.sql to create tables if they don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = await self.get_connection()
        await conn.executescript(schema_sql)
        await conn.commit()
        logger.info("database_schema_initialized")

    async def get_connection(self) -> aiosqlite.Connection:
        """Return the active database connection."""
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("database_closed")

    async def execute(
        self, query: str, params: tuple | dict | None = None
    ) -> aiosqlite.Cursor:
        """Execute a single parameterized query."""
        conn = await self.get_connection()
        cursor = await conn.execute(query, params or ())
        await conn.commit()
        return cursor

    async def fetch_one(
        self, query: str, params: tuple | dict | None = None
    ) -> aiosqlite.Row | None:
        """Execute query and return a single row."""
        conn = await self.get_connection()
        cursor = await conn.execute(query, params or ())
        return await cursor.fetchone()

    async def fetch_all(
        self, query: str, params: tuple | dict | None = None
    ) -> list[aiosqlite.Row]:
        """Execute query and return all rows."""
        conn = await self.get_connection()
        cursor = await conn.execute(query, params or ())
        return await cursor.fetchall()


def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    if _DB_INSTANCE is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _DB_INSTANCE


def init_database(db_path: str) -> DatabaseManager:
    """Create and store the global database manager instance."""
    global _DB_INSTANCE
    _DB_INSTANCE = DatabaseManager(db_path)
    return _DB_INSTANCE
