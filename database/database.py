"""
database/database.py
Thin async data-access layer around aiosqlite.
All queries are parameterized. One shared connection guarded by an asyncio.Lock
is used since SQLite handles single-writer access poorly under concurrency —
this avoids "database is locked" errors under discord.py's async event loop.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable, Optional

import aiosqlite

from database.models import INDEX_STATEMENTS, SCHEMA_STATEMENTS

logger = logging.getLogger("masteragent.database")


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.execute("PRAGMA journal_mode = WAL;")
        await self._conn.commit()
        await self._init_schema()
        logger.info("Base de données connectée: %s", self.path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _init_schema(self) -> None:
        assert self._conn is not None
        async with self._lock:
            for stmt in SCHEMA_STATEMENTS:
                await self._conn.execute(stmt)
            for stmt in INDEX_STATEMENTS:
                await self._conn.execute(stmt)
            await self._conn.commit()

    # ---------- low-level helpers ----------

    async def execute(self, query: str, params: Iterable[Any] = ()) -> int:
        assert self._conn is not None
        async with self._lock:
            cursor = await self._conn.execute(query, tuple(params))
            await self._conn.commit()
            return cursor.lastrowid

    async def fetchone(self, query: str, params: Iterable[Any] = ()) -> Optional[aiosqlite.Row]:
        assert self._conn is not None
        async with self._lock:
            cursor = await self._conn.execute(query, tuple(params))
            row = await cursor.fetchone()
            await cursor.close()
            return row

    async def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[aiosqlite.Row]:
        assert self._conn is not None
        async with self._lock:
            cursor = await self._conn.execute(query, tuple(params))
            rows = await cursor.fetchall()
            await cursor.close()
            return rows

    # ---------- guilds / configuration ----------

    async def ensure_guild(self, guild_id: int) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO guilds (guild_id) VALUES (?)", (guild_id,)
        )

    async def get_guild_config(self, guild_id: int) -> Optional[aiosqlite.Row]:
        return await self.fetchone("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,))

    async def update_guild_config(self, guild_id: int, **fields: Any) -> None:
        if not fields:
            return
        await self.ensure_guild(guild_id)
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [guild_id]
        await self.execute(
            f"UPDATE guilds SET {columns}, updated_at = datetime('now') WHERE guild_id = ?",
            values,
        )

    # ---------- server resources (setup idempotency) ----------

    async def get_resource(self, guild_id: int, resource_type: str, resource_key: str) -> Optional[int]:
        row = await self.fetchone(
            "SELECT discord_id FROM server_resources WHERE guild_id=? AND resource_type=? AND resource_key=?",
            (guild_id, resource_type, resource_key),
        )
        return row["discord_id"] if row else None

    async def save_resource(self, guild_id: int, resource_type: str, resource_key: str, discord_id: int) -> None:
        await self.execute(
            """INSERT INTO server_resources (guild_id, resource_type, resource_key, discord_id)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(guild_id, resource_type, resource_key)
               DO UPDATE SET discord_id = excluded.discord_id""",
            (guild_id, resource_type, resource_key, discord_id),
        )

    # ---------- members ----------

    async def upsert_member(self, guild_id: int, user_id: int) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO members (guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )

    async def set_member_verified(self, guild_id: int, user_id: int, verified: bool) -> None:
        await self.upsert_member(guild_id, user_id)
        await self.execute(
            "UPDATE members SET verified=? WHERE guild_id=? AND user_id=?",
            (int(verified), guild_id, user_id),
        )

    # ---------- warnings & moderation ----------

    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        return await self.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, reason),
        )

    async def get_warnings(self, guild_id: int, user_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY created_at DESC",
            (guild_id, user_id),
        )

    async def count_warnings(self, guild_id: int, user_id: int) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) as c FROM warnings WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
        return row["c"] if row else 0

    async def clear_warnings(self, guild_id: int, user_id: int) -> None:
        await self.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))

    async def log_moderation_action(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        action: str,
        reason: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> int:
        return await self.execute(
            """INSERT INTO moderation_logs (guild_id, user_id, moderator_id, action, reason, duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (guild_id, user_id, moderator_id, action, reason, duration_seconds),
        )

    # ---------- tickets ----------

    async def next_ticket_number(self, guild_id: int) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) as c FROM tickets WHERE guild_id=?", (guild_id,)
        )
        return (row["c"] if row else 0) + 1

    async def create_ticket(
        self, guild_id: int, channel_id: int, opener_id: int, category: str, ticket_number: int
    ) -> int:
        return await self.execute(
            """INSERT INTO tickets (guild_id, channel_id, opener_id, category, ticket_number)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, channel_id, opener_id, category, ticket_number),
        )

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[aiosqlite.Row]:
        return await self.fetchone("SELECT * FROM tickets WHERE channel_id=?", (channel_id,))

    async def claim_ticket(self, channel_id: int, staff_id: int) -> None:
        await self.execute(
            "UPDATE tickets SET status='claimed', claimed_by=? WHERE channel_id=?",
            (staff_id, channel_id),
        )

    async def close_ticket(self, channel_id: int, closed_by: int, reason: Optional[str]) -> None:
        await self.execute(
            """UPDATE tickets SET status='closed', closed_by=?, close_reason=?, closed_at=datetime('now')
               WHERE channel_id=?""",
            (closed_by, reason, channel_id),
        )

    # ---------- projects ----------

    async def create_project(
        self,
        guild_id: int,
        author_id: int,
        name: str,
        description: str,
        technologies: str,
        github_link: str,
        demo_link: str,
        seeking_collaborators: bool,
    ) -> int:
        return await self.execute(
            """INSERT INTO projects
               (guild_id, author_id, name, description, technologies, github_link, demo_link, seeking_collaborators)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                guild_id, author_id, name, description, technologies,
                github_link, demo_link, int(seeking_collaborators),
            ),
        )

    async def set_project_message(self, project_id: int, message_id: int, channel_id: int) -> None:
        await self.execute(
            "UPDATE projects SET message_id=?, channel_id=? WHERE id=?",
            (message_id, channel_id, project_id),
        )

    # ---------- profiles ----------

    async def upsert_profile(self, guild_id: int, user_id: int, **fields: Any) -> None:
        existing = await self.fetchone(
            "SELECT id FROM profiles WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        )
        if existing:
            columns = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [guild_id, user_id]
            await self.execute(
                f"UPDATE profiles SET {columns}, updated_at = datetime('now') WHERE guild_id=? AND user_id=?",
                values,
            )
        else:
            keys = ["guild_id", "user_id"] + list(fields.keys())
            placeholders = ", ".join("?" for _ in keys)
            values = [guild_id, user_id] + list(fields.values())
            await self.execute(
                f"INSERT INTO profiles ({', '.join(keys)}) VALUES ({placeholders})", values
            )

    async def get_profile(self, guild_id: int, user_id: int) -> Optional[aiosqlite.Row]:
        return await self.fetchone(
            "SELECT * FROM profiles WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        )

    # ---------- staff ----------

    async def add_staff_member(self, guild_id: int, user_id: int, role_label: str, actor_id: int) -> None:
        await self.execute(
            """INSERT INTO staff_members (guild_id, user_id, role_label)
               VALUES (?, ?, ?)
               ON CONFLICT(guild_id, user_id) DO UPDATE SET role_label=excluded.role_label, active=1""",
            (guild_id, user_id, role_label),
        )
        await self.log_staff_action(guild_id, user_id, actor_id, "added", role_label)

    async def remove_staff_member(self, guild_id: int, user_id: int, actor_id: int) -> None:
        await self.execute(
            "UPDATE staff_members SET active=0 WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
        await self.log_staff_action(guild_id, user_id, actor_id, "removed", None)

    async def list_staff(self, guild_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM staff_members WHERE guild_id=? AND active=1 ORDER BY joined_staff_at",
            (guild_id,),
        )

    async def log_staff_action(
        self, guild_id: int, staff_user_id: int, actor_id: int, action: str, details: Optional[str]
    ) -> None:
        await self.execute(
            """INSERT INTO staff_actions (guild_id, staff_user_id, actor_id, action, details)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, staff_user_id, actor_id, action, details),
        )

    async def increment_staff_actions(self, guild_id: int, user_id: int) -> None:
        await self.execute(
            "UPDATE staff_members SET actions_count = actions_count + 1 WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
