"""
NovaMart - Database Connection
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Try to load .env for local development if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Prefer a single DATABASE_URL, otherwise construct a config from DB_* vars.
_DATABASE_URL = os.getenv("DATABASE_URL")
if _DATABASE_URL:
    def get_connection():
        """Get a new database connection using a DSN from DATABASE_URL."""
        return psycopg2.connect(_DATABASE_URL)
else:
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME", "nova_market"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASS", ""),
    }

    def get_connection():
        """Get a new database connection using individual environment variables."""
        return psycopg2.connect(**DB_CONFIG)


def query(sql, params=None):
    """Execute a query and return results as list of dicts."""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        results = cur.fetchall()
        cur.close()
        return results
    finally:
        conn.close()


def query_one(sql, params=None):
    """Execute a query and return a single result."""
    results = query(sql, params)
    return results[0] if results else None


def execute(sql, params=None):
    """Execute an INSERT/UPDATE/DELETE and return the id (if RETURNING) or rowcount."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        try:
            result = cur.fetchone()
            cur.close()
            return result[0] if result else None
        except Exception:
            cur.close()
            return cur.rowcount
    finally:
        conn.close()
