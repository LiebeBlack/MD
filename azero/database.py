"""Base de datos local (SQLite) del launcher.

Guarda el historial de descargas/instalaciones, las sesiones de juego y
las cuentas de Microsoft. Todo vive en ``data/launcher.db`` junto al resto
de datos portables del launcher.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from typing import Any

from . import paths

_SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    version_id TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ok',
    detail TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started REAL NOT NULL,
    ended REAL,
    username TEXT NOT NULL DEFAULT '',
    uuid TEXT NOT NULL DEFAULT '',
    version_id TEXT NOT NULL DEFAULT '',
    account TEXT NOT NULL DEFAULT 'offline',
    pid INTEGER,
    exit_code INTEGER,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL DEFAULT 'microsoft',
    mc_uuid TEXT NOT NULL DEFAULT '',
    mc_name TEXT NOT NULL DEFAULT '',
    msa_refresh_token TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_downloads_ts ON downloads(ts);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started);
"""

_lock = threading.Lock()


def _db_path() -> Path:
    paths.ensure_dirs()
    return paths.DATA_DIR / "launcher.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), timeout=10,
                           isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _lock, closing(_connect()) as conn:
        conn.executescript(_SCHEMA)


# ------------------------------------------------------------- descargas
def log_download(kind: str, label: str, version_id: str = "",
                 size_bytes: int = 0, status: str = "ok",
                 detail: str = "") -> int:
    """Registra un evento de descarga/instalacion. Devuelve el id."""
    with _lock, closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO downloads (ts, kind, label, version_id, size_bytes,"
            " status, detail) VALUES (?,?,?,?,?,?,?)",
            (time.time(), kind, label, version_id, int(size_bytes),
             status, detail),
        )
        return int(cur.lastrowid)


def list_downloads(limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with _lock, closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM downloads ORDER BY ts DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


# -------------------------------------------------------------- sesiones
def session_start(username: str, uuid_: str, version_id: str,
                  account: str, pid: int | None = None) -> int:
    with _lock, closing(_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO sessions (started, username, uuid, version_id,"
            " account, pid) VALUES (?,?,?,?,?,?)",
            (time.time(), username, uuid_, version_id, account, pid),
        )
        return int(cur.lastrowid)


def session_end(session_id: int, exit_code: int | None = None,
                detail: str = "") -> None:
    with _lock, closing(_connect()) as conn:
        conn.execute(
            "UPDATE sessions SET ended=?, exit_code=?, detail=? WHERE id=?",
            (time.time(), exit_code, detail, int(session_id)),
        )


def list_sessions(limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with _lock, closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


# -------------------------------------------------------------- cuentas
def save_account(mc_uuid: str, mc_name: str, refresh_token: str) -> None:
    """Guarda o actualiza una cuenta Microsoft (id = UUID de Minecraft)."""
    with _lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO accounts (id, provider, mc_uuid, mc_name,"
            " msa_refresh_token, created) VALUES (?, 'microsoft', ?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET mc_name=excluded.mc_name,"
            " msa_refresh_token=excluded.msa_refresh_token",
            (mc_uuid, mc_uuid, mc_name, refresh_token, time.time()),
        )


def list_accounts() -> list[dict[str, Any]]:
    init_db()
    with _lock, closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, mc_uuid, mc_name, created FROM accounts"
            " ORDER BY mc_name"
        ).fetchall()
    return [dict(row) for row in rows]


def get_account(account_id: str) -> dict[str, Any] | None:
    init_db()
    with _lock, closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id=?", (account_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_account(account_id: str) -> None:
    with _lock, closing(_connect()) as conn:
        conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))


def clear_history(kind: str | None = None) -> int:
    """Borra historial. kind=None limpia descargas y sesiones."""
    with _lock, closing(_connect()) as conn:
        if kind is None:
            cur = conn.execute("DELETE FROM downloads")
            conn.execute("DELETE FROM sessions")
        else:
            cur = conn.execute("DELETE FROM downloads WHERE kind=?", (kind,))
        return int(cur.rowcount)


__all__ = [
    "init_db", "log_download", "list_downloads", "session_start",
    "session_end", "list_sessions", "save_account", "list_accounts",
    "get_account", "delete_account", "clear_history",
]
