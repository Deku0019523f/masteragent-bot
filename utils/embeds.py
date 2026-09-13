"""
utils/embeds.py
Centralized embed builders so message styling stays consistent across cogs.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import discord

COLOR_PRIMARY = 0x5865F2
COLOR_SUCCESS = 0x2ECC71
COLOR_WARNING = 0xF1C40F
COLOR_DANGER = 0xE74C3C
COLOR_INFO = 0x3498DB
COLOR_STAFF = 0x9B59B6

FOOTER_TEXT = "Master Agent • Agents IA pour WhatsApp"


def _base(title: str, description: str = "", color: int = COLOR_PRIMARY) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, timestamp=dt.datetime.utcnow())
    embed.set_footer(text=FOOTER_TEXT)
    return embed


def success(title: str, description: str = "") -> discord.Embed:
    return _base(f"✅ {title}", description, COLOR_SUCCESS)


def error(title: str, description: str = "") -> discord.Embed:
    return _base(f"❌ {title}", description, COLOR_DANGER)


def warning(title: str, description: str = "") -> discord.Embed:
    return _base(f"⚠️ {title}", description, COLOR_WARNING)


def info(title: str, description: str = "") -> discord.Embed:
    return _base(f"ℹ️ {title}", description, COLOR_INFO)


def moderation_log(
    action: str,
    member: discord.abc.User,
    moderator: discord.abc.User,
    reason: str,
    duration: Optional[str] = None,
) -> discord.Embed:
    embed = _base("🛡️ MODÉRATION", color=COLOR_DANGER)
    embed.add_field(name="Membre", value=member.mention, inline=True)
    embed.add_field(name="Action", value=action, inline=True)
    if duration:
        embed.add_field(name="Durée", value=duration, inline=True)
    embed.add_field(name="Modérateur", value=moderator.mention, inline=True)
    embed.add_field(name="Raison", value=reason or "Aucune raison fournie", inline=False)
    return embed


def project_embed(
    author: discord.abc.User,
    name: str,
    description: str,
    technologies: str,
    doc_link: str,
    demo_link: str,
    seeking_feedback: bool,
) -> discord.Embed:
    """Embed de présentation d'un agent IA créé sur Master Agent."""
    embed = _base(f"🤖 {name}", description, COLOR_PRIMARY)
    if technologies:
        embed.add_field(name="🛠️ Intégrations", value=technologies, inline=False)
    if seeking_feedback:
        embed.add_field(name="💬 Retours", value="Ouvert aux retours de la communauté", inline=False)
    links = []
    if doc_link:
        links.append(f"[Documentation]({doc_link})")
    if demo_link:
        links.append(f"[Démo]({demo_link})")
    if links:
        embed.add_field(name="🔗 Liens", value=" • ".join(links), inline=False)
    embed.set_footer(text=f"Créé par {author.display_name} • {FOOTER_TEXT}")
    if isinstance(author, (discord.Member, discord.User)) and author.display_avatar:
        embed.set_author(name=str(author), icon_url=author.display_avatar.url)
    return embed


def profile_embed(member: discord.abc.User, profile_row) -> discord.Embed:
    embed = _base(f"👤 Profil de {member.display_name}", color=COLOR_INFO)
    if isinstance(member, (discord.Member, discord.User)) and member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)
    if profile_row is None:
        embed.description = "Ce membre n'a pas encore configuré son profil."
        return embed
    if profile_row["domain"]:
        embed.add_field(name="Domaine", value=profile_row["domain"], inline=True)
    if profile_row["technologies"]:
        embed.add_field(name="Technologies", value=profile_row["technologies"], inline=True)
    if profile_row["skills"]:
        embed.add_field(name="Compétences", value=profile_row["skills"], inline=False)
    if profile_row["bio"]:
        embed.add_field(name="Bio", value=profile_row["bio"], inline=False)
    links = []
    if profile_row["github"]:
        links.append(f"[GitHub]({profile_row['github']})")
    if profile_row["portfolio"]:
        links.append(f"[Portfolio]({profile_row['portfolio']})")
    if profile_row["socials"]:
        links.append(profile_row["socials"])
    if links:
        embed.add_field(name="🔗 Liens", value=" • ".join(links), inline=False)
    return embed
