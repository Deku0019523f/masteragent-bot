"""
tests/test_database.py
Exercises the Database layer against a temporary SQLite file.
No Discord token required — pure data-layer tests.
"""
import asyncio
import os
import tempfile

import pytest

from database.database import Database

GUILD_ID = 111111111111111111
USER_ID = 222222222222222222
MOD_ID = 333333333333333333


@pytest.fixture
async def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    await database.connect()
    yield database
    await database.close()
    os.remove(path)


@pytest.mark.asyncio
async def test_schema_initializes(db):
    row = await db.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='guilds'")
    assert row is not None


@pytest.mark.asyncio
async def test_guild_config_roundtrip(db):
    await db.ensure_guild(GUILD_ID)
    config = await db.get_guild_config(GUILD_ID)
    assert config is not None
    assert config["setup_status"] == "not_started"

    await db.update_guild_config(GUILD_ID, setup_status="completed", welcome_channel=123)
    config = await db.get_guild_config(GUILD_ID)
    assert config["setup_status"] == "completed"
    assert config["welcome_channel"] == 123


@pytest.mark.asyncio
async def test_warnings_flow(db):
    await db.ensure_guild(GUILD_ID)
    await db.add_warning(GUILD_ID, USER_ID, MOD_ID, "Spam")
    await db.add_warning(GUILD_ID, USER_ID, MOD_ID, "Insultes")

    count = await db.count_warnings(GUILD_ID, USER_ID)
    assert count == 2

    rows = await db.get_warnings(GUILD_ID, USER_ID)
    assert len(rows) == 2
    assert rows[0]["reason"] in {"Spam", "Insultes"}

    await db.clear_warnings(GUILD_ID, USER_ID)
    assert await db.count_warnings(GUILD_ID, USER_ID) == 0


@pytest.mark.asyncio
async def test_resource_idempotency(db):
    await db.ensure_guild(GUILD_ID)
    await db.save_resource(GUILD_ID, "role", "🌱 Nouveau membre", 999)
    discord_id = await db.get_resource(GUILD_ID, "role", "🌱 Nouveau membre")
    assert discord_id == 999

    # Re-saving with a new id should update, not duplicate.
    await db.save_resource(GUILD_ID, "role", "🌱 Nouveau membre", 1000)
    discord_id = await db.get_resource(GUILD_ID, "role", "🌱 Nouveau membre")
    assert discord_id == 1000

    rows = await db.fetchall(
        "SELECT * FROM server_resources WHERE guild_id=? AND resource_key=?", (GUILD_ID, "🌱 Nouveau membre")
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_profile_upsert(db):
    await db.ensure_guild(GUILD_ID)
    await db.upsert_profile(GUILD_ID, USER_ID, domain="IA", bio="Passionné de vibe coding")
    profile = await db.get_profile(GUILD_ID, USER_ID)
    assert profile["domain"] == "IA"

    await db.upsert_profile(GUILD_ID, USER_ID, domain="Backend")
    profile = await db.get_profile(GUILD_ID, USER_ID)
    assert profile["domain"] == "Backend"
    assert profile["bio"] == "Passionné de vibe coding"  # untouched field preserved


@pytest.mark.asyncio
async def test_ticket_creation_and_numbering(db):
    await db.ensure_guild(GUILD_ID)
    n1 = await db.next_ticket_number(GUILD_ID)
    await db.create_ticket(GUILD_ID, 555, USER_ID, "support", n1)
    n2 = await db.next_ticket_number(GUILD_ID)
    assert n2 == n1 + 1

    ticket = await db.get_ticket_by_channel(555)
    assert ticket["status"] == "open"

    await db.claim_ticket(555, MOD_ID)
    ticket = await db.get_ticket_by_channel(555)
    assert ticket["status"] == "claimed"
    assert ticket["claimed_by"] == MOD_ID

    await db.close_ticket(555, MOD_ID, "Résolu")
    ticket = await db.get_ticket_by_channel(555)
    assert ticket["status"] == "closed"
    assert ticket["close_reason"] == "Résolu"


@pytest.mark.asyncio
async def test_staff_roster(db):
    await db.ensure_guild(GUILD_ID)
    await db.add_staff_member(GUILD_ID, USER_ID, "Modérateur", MOD_ID)
    staff = await db.list_staff(GUILD_ID)
    assert len(staff) == 1
    assert staff[0]["role_label"] == "Modérateur"

    await db.remove_staff_member(GUILD_ID, USER_ID, MOD_ID)
    staff = await db.list_staff(GUILD_ID)
    assert len(staff) == 0
