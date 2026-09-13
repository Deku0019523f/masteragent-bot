"""
utils/rules_message.py
Logique partagée pour (re)poster le panneau de règlement (embed + bouton
"J'accepte le règlement") dans le salon #reglement. Utilisé par /setup
(première installation) et par /reglement definir|reinitialiser (mise à
jour du texte affiché), afin que le salon reflète toujours le texte
actuellement configuré en base.
"""
from __future__ import annotations

import discord

from utils import embeds


async def sync_rules_panel(
    bot, guild: discord.Guild, rules_channel: discord.TextChannel, rules_text: str
) -> discord.Message:
    """Édite le message du panneau de règlement déjà posté par le bot dans ce
    salon (identifié par la présence de components), sinon en poste un nouveau.
    Retourne le message résultant."""
    from views.welcome_view import RulesAcceptView

    embed = embeds.info("📜 Règlement Master Agent", rules_text)
    async for message in rules_channel.history(limit=20):
        if message.author == guild.me and message.components:
            await message.edit(embed=embed, view=RulesAcceptView(bot))
            return message
    return await rules_channel.send(embed=embed, view=RulesAcceptView(bot))
