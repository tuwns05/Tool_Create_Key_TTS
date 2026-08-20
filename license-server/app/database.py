"""SQLite connection and schema layer for test orders."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .settings import get_database_path


SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_order TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    plan TEXT NOT NULL CHECK (plan IN ('monthly', 'yearly')),
    price INTEGER NOT NULL CHECK (price > 0),
    mac TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('PENDING', 'PAID', 'LICENSE_CREATED', 'LICENSE_SENT')
    ),
    created_at TEXT NOT NULL,
    paid_at TEXT,
    expires_at TEXT,
    license_key TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_id_order ON orders(id_order);
"""


def connect() -> sqlite3.Connection:
    path = get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize_database() -> None:
    connection = connect()
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    initialize_database()
    connection = connect()
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()
