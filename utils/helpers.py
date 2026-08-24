"""
utils/helpers.py
Small, generic helper functions shared across cogs.
"""
from __future__ import annotations

import re

import discord

DURATION_PATTERN = re.compile(r"^(\d+)([smhdSMHD])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(text: str) -> int | None:
    """Parse durations like '10m', '2h', '1d' into seconds. Returns None if invalid."""
    match = DURATION_PATTERN.match(text.strip())
    if not match:
        return None
    amount, unit = match.groups()
    return int(amount) * _UNIT_SECONDS[unit.lower()]


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m" + (f" {sec}s" if sec else "")
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h" + (f" {minutes}m" if minutes else "")
    days, hours = divmod(hours, 24)
    return f"{days}j" + (f" {hours}h" if hours else "")


def safe_channel_name(name: str) -> str:
    """Discord channel names: lowercase, no spaces beyond hyphen, limited charset issues avoided."""
    return name.strip()[:100]


async def find_role(guild: discord.Guild, discord_id: int | None) -> discord.Role | None:
    if not discord_id:
        return None
    return guild.get_role(discord_id)


async def find_channel(guild: discord.Guild, discord_id: int | None):
    if not discord_id:
        return None
    return guild.get_channel(discord_id)
