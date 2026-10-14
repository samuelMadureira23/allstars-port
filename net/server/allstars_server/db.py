"""Banco SQLite do servidor: contas, placares (sceNpScore) e TUS (sceNpTus)."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
import time
from dataclasses import dataclass

ONLINE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{2,15}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    online_id   TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pw_salt     BLOB NOT NULL,
    pw_hash     BLOB NOT NULL,
    created     INTEGER NOT NULL,
    last_login  INTEGER,
    banned      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS scores (
    board       INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    pcid        INTEGER NOT NULL DEFAULT 0,
    score       INTEGER NOT NULL,
    comment     TEXT NOT NULL DEFAULT '',
    game_info   BLOB NOT NULL DEFAULT x'',
    updated     INTEGER NOT NULL,
    PRIMARY KEY (board, user_id, pcid)
);
CREATE INDEX IF NOT EXISTS scores_rank ON scores (board, score DESC, updated ASC);
CREATE TABLE IF NOT EXISTS tus_vars (
    owner       INTEGER NOT NULL,
    slot        INTEGER NOT NULL,
    value       INTEGER NOT NULL,
    setter      INTEGER NOT NULL,
    updated     INTEGER NOT NULL,
    PRIMARY KEY (owner, slot)
);
CREATE TABLE IF NOT EXISTS tus_data (
    owner       INTEGER NOT NULL,
    slot        INTEGER NOT NULL,
    data        BLOB NOT NULL,
    info        BLOB NOT NULL DEFAULT x'',
    setter      INTEGER NOT NULL,
    updated     INTEGER NOT NULL,
    PRIMARY KEY (owner, slot)
);
"""


@dataclass
class Account:
    user_id: int
    online_id: str
    created: int
    banned: bool


def _hash_pw(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


class Database:
    def __init__(self, path: str) -> None:
        self.conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # -- contas ---------------------------------------------------------------
    def get_account(self, online_id: str) -> Account | None:
        row = self.conn.execute(
            "SELECT user_id, online_id, created, banned FROM accounts WHERE online_id = ?", (online_id,)
        ).fetchone()
        return Account(row[0], row[1], row[2], bool(row[3])) if row else None

    def get_account_by_id(self, user_id: int) -> Account | None:
        row = self.conn.execute(
            "SELECT user_id, online_id, created, banned FROM accounts WHERE user_id = ?", (user_id,)
        ).fetchone()
        return Account(row[0], row[1], row[2], bool(row[3])) if row else None

    def create_account(self, online_id: str, password: str) -> Account:
        if not ONLINE_ID_RE.match(online_id):
            raise ValueError("online id invalido")
        salt = os.urandom(16)
        now = int(time.time())
        cur = self.conn.execute(
            "INSERT INTO accounts (online_id, pw_salt, pw_hash, created) VALUES (?, ?, ?, ?)",
            (online_id, salt, _hash_pw(password, salt), now),
        )
        return Account(cur.lastrowid, online_id, now, False)

    def check_password(self, online_id: str, password: str) -> bool:
        row = self.conn.execute(
            "SELECT pw_salt, pw_hash FROM accounts WHERE online_id = ?", (online_id,)
        ).fetchone()
        return bool(row) and hmac.compare_digest(_hash_pw(password, row[0]), row[1])

    def touch_login(self, user_id: int) -> None:
        self.conn.execute("UPDATE accounts SET last_login = ? WHERE user_id = ?", (int(time.time()), user_id))

    # -- placares -------------------------------------------------------------
    def record_score(self, board: int, user_id: int, pcid: int, score: int, comment: str,
                     game_info: bytes, higher_is_better: bool = True) -> tuple[int, bool]:
        """Grava se for recorde do jogador. Devolve (rank, gravou)."""
        row = self.conn.execute(
            "SELECT score FROM scores WHERE board = ? AND user_id = ? AND pcid = ?", (board, user_id, pcid)
        ).fetchone()
        better = row is None or (score > row[0] if higher_is_better else score < row[0])
        if better:
            self.conn.execute(
                "INSERT OR REPLACE INTO scores (board, user_id, pcid, score, comment, game_info, updated)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (board, user_id, pcid, score, comment, game_info, int(time.time())),
            )
        return self.rank_of(board, user_id, pcid), better

    def rank_of(self, board: int, user_id: int, pcid: int) -> int:
        row = self.conn.execute(
            "SELECT score, updated FROM scores WHERE board = ? AND user_id = ? AND pcid = ?",
            (board, user_id, pcid),
        ).fetchone()
        if row is None:
            return 0
        above = self.conn.execute(
            "SELECT COUNT(*) FROM scores WHERE board = ? AND (score > ? OR (score = ? AND updated < ?))",
            (board, row[0], row[0], row[1]),
        ).fetchone()[0]
        return above + 1

    def score_range(self, board: int, start_rank: int, count: int) -> tuple[int, list[tuple]]:
        """Entradas a partir de start_rank (1 = primeiro). Devolve (total, [(rank, online_id, pcid,
        score, comment, game_info, updated)])."""
        total = self.conn.execute("SELECT COUNT(*) FROM scores WHERE board = ?", (board,)).fetchone()[0]
        rows = self.conn.execute(
            "SELECT a.online_id, s.pcid, s.score, s.comment, s.game_info, s.updated"
            " FROM scores s JOIN accounts a ON a.user_id = s.user_id"
            " WHERE s.board = ? ORDER BY s.score DESC, s.updated ASC LIMIT ? OFFSET ?",
            (board, count, max(0, start_rank - 1)),
        ).fetchall()
        return total, [(start_rank + i, *r) for i, r in enumerate(rows)]

    def score_of(self, board: int, online_id: str, pcid: int) -> tuple | None:
        acc = self.get_account(online_id)
        if acc is None:
            return None
        row = self.conn.execute(
            "SELECT score, comment, game_info, updated FROM scores WHERE board = ? AND user_id = ? AND pcid = ?",
            (board, acc.user_id, pcid),
        ).fetchone()
        if row is None:
            return None
        return (self.rank_of(board, acc.user_id, pcid), acc.online_id, pcid, *row)

    # -- TUS ------------------------------------------------------------------
    def tus_set_var(self, owner: int, slot: int, value: int, setter: int) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO tus_vars (owner, slot, value, setter, updated) VALUES (?, ?, ?, ?, ?)",
            (owner, slot, value, setter, int(time.time())),
        )

    def tus_get_var(self, owner: int, slot: int) -> tuple | None:
        return self.conn.execute(
            "SELECT value, setter, updated FROM tus_vars WHERE owner = ? AND slot = ?", (owner, slot)
        ).fetchone()

    def tus_set_data(self, owner: int, slot: int, data: bytes, info: bytes, setter: int) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO tus_data (owner, slot, data, info, setter, updated) VALUES (?, ?, ?, ?, ?, ?)",
            (owner, slot, data, info, setter, int(time.time())),
        )

    def tus_get_data(self, owner: int, slot: int) -> tuple | None:
        return self.conn.execute(
            "SELECT data, info, setter, updated FROM tus_data WHERE owner = ? AND slot = ?", (owner, slot)
        ).fetchone()

    def tus_delete(self, owner: int, slot: int) -> None:
        self.conn.execute("DELETE FROM tus_vars WHERE owner = ? AND slot = ?", (owner, slot))
        self.conn.execute("DELETE FROM tus_data WHERE owner = ? AND slot = ?", (owner, slot))
