# -*- coding: utf-8 -*-
"""
Database Pool - Gestión de conexiones a PostgreSQL
"""

import psycopg2
from psycopg2 import pool
import logging
from typing import Generator
import threading
import time

from config import settings

logger = logging.getLogger(__name__)

class DatabasePool:
    """Pool de conexiones a PostgreSQL"""
    
    _pool = None
    _lock = threading.Lock()
    _active_connections = 0
    
    @classmethod
    def init_pool(cls):
        """Inicializar pool de conexiones"""
        if cls._pool is not None:
            return

        try:
            with cls._lock:
                if cls._pool is not None:
                    return

                min_conn = max(1, int(settings.DB_POOL_MIN))
                max_conn = max(min_conn, int(settings.DB_POOL_MAX), 200)

                cls._pool = psycopg2.pool.ThreadedConnectionPool(
                    min_conn,
                    max_conn,
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    database=settings.DB_NAME,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    sslmode="require",
                    connect_timeout=int(settings.DB_CONNECT_TIMEOUT),
                    application_name="paintflow_api",
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=3,
                )
                cls._active_connections = 0
                logger.info(f"✅ DatabasePool initialized (min={min_conn}, max={max_conn})")
        except Exception as e:
            logger.error(f"❌ Error initializing DatabasePool: {e}")
            raise
    
    @classmethod
    def get_connection(cls):
        """Obtener conexión del pool"""
        if cls._pool is None:
            cls.init_pool()

        retries = max(0, int(settings.DB_POOL_GET_RETRIES))
        backoff = max(0.05, float(settings.DB_POOL_GET_BACKOFF_SEC))

        for attempt in range(retries + 1):
            try:
                conn = cls._pool.getconn()
                with cls._lock:
                    cls._active_connections += 1
                return conn
            except psycopg2.pool.PoolError:
                if attempt >= retries:
                    break
                time.sleep(backoff * (attempt + 1))

        with cls._lock:
            active = cls._active_connections
        raise RuntimeError(f"Database pool exhausted (active={active})")
    
    @classmethod
    def return_connection(cls, conn, close: bool = False):
        """Devolver conexión al pool"""
        if conn is None:
            return

        if cls._pool is None:
            try:
                conn.close()
            except Exception:
                pass
            return

        should_close = close
        try:
            if getattr(conn, "closed", 1) != 0:
                should_close = True
        except Exception:
            should_close = True

        try:
            cls._pool.putconn(conn, close=should_close)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
        finally:
            with cls._lock:
                if cls._active_connections > 0:
                    cls._active_connections -= 1
    
    @classmethod
    def close_pool(cls):
        """Cerrar pool de conexiones"""
        with cls._lock:
            if cls._pool is not None:
                cls._pool.closeall()
                cls._pool = None
                cls._active_connections = 0
                logger.info("✅ DatabasePool closed")

def get_db() -> Generator:
    """Dependency para FastAPI que proporciona una conexión a la BD"""
    conn = DatabasePool.get_connection()
    try:
        yield conn
    except Exception:
        # En caso de error, hacer rollback
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        # Siempre devolver conexión al pool
        DatabasePool.return_connection(conn)
