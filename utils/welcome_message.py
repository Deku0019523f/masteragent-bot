"""
utils/welcome_message.py
Rend le gabarit du message de bienvenue en remplaçant les variables par les
valeurs réelles du membre/serveur. Utilisé par cogs/welcome.py (envoi réel à
l'arrivée d'un membre) et cogs/customization.py (aperçu via /bienvenue voir).

Variables disponibles dans le gabarit :
    {member_mention}  → mention du membre (@Membre)
    {member_name}      → pseudo affiché du membre
    {server_name}       → nom du serveur
    {rules_channel}      → mention du salon règlement (ou "#reglement" si absent)
"""
from __future__ import annotations

from typing import Optional

import discord


def render_welcome_message(
    template: str,
    member: discord.Member,
    rules_channel: Optional[discord.abc.GuildChannel],
) -> str:
    return (
        template.replace("{member_mention}", member.mention)
        .replace("{member_name}", member.display_name)
        .replace("{server_name}", member.guild.name)
        .replace("{rules_channel}", rules_channel.mention if rules_channel else "#reglement")
    )
