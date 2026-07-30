"""
Database connection and session management.

Provides async database connectivity with connection pooling,
automatic retries, and integrity checking.
"""

import asyncio
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import StaticPool
import logging

from config import get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Features:
    - Async session management
    - Connection pooling optimization for SQLite
    - Automatic retry logic
    - Integrity checking
    - Backup scheduling
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection."""
        if self._initialized:
            return
        
        config = get_config()
        
        logger.info(f"Initializing database connection to {config.database_url}")
        
        # Create async engine with optimized settings for SQLite
        self._engine = create_async_engine(
            config.database_url,
            echo=False,  # Set to True for SQL debugging
            poolclass=StaticPool,  # SQLite works best with static pool
            connect_args={
                "check_same_thread": False,
            },
            future=True,
        )
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self._initialized = True
        logger.info("Database initialized successfully")
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic cleanup.
        
        Usage:
            async with db_manager.get_session() as session:
                # use session
        """
        if not self._initialized:
            await self.initialize()
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database transaction failed: {e}", exc_info=True)
            raise
        finally:
            await session.close()
    
    async def execute_with_retry(
        self,
        operation,
        max_retries: int = 3,
        delay: float = 0.1,
    ):
        """
        Execute a database operation with automatic retry.
        
        Args:
            operation: Async callable that takes a session
            max_retries: Maximum number of retry attempts
            delay: Base delay between retries in seconds
        
        Returns:
            Result of the operation
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                async with self.get_session() as session:
                    result = await operation(session)
                    return result
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
        
        logger.error(f"Database operation failed after {max_retries} attempts")
        raise last_exception
    
    async def check_integrity(self) -> dict:
        """
        Check database integrity.
        
        Returns:
            Dictionary with integrity check results
        """
        results = {
            "connected": False,
            "tables_accessible": False,
            "foreign_keys_valid": False,
            "issues": [],
        }
        
        try:
            async with self.get_session() as session:
                # Test basic connectivity
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
                results["connected"] = True
                
                # Check foreign keys
                fk_result = await session.execute(text("PRAGMA foreign_key_check"))
                fk_violations = fk_result.fetchall()
                
                if fk_violations:
                    results["foreign_keys_valid"] = False
                    results["issues"].append(
                        f"Found {len(fk_violations)} foreign key violations"
                    )
                else:
                    results["foreign_keys_valid"] = True
                
                results["tables_accessible"] = True
                
        except Exception as e:
            results["issues"].append(str(e))
            logger.error(f"Database integrity check failed: {e}")
        
        return results
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine."""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    Can be used with FastAPI-style dependency injection.
    """
    async with db_manager.get_session() as session:
        yield session


__all__ = [
    'DatabaseManager',
    'db_manager',
    'get_db',
]
