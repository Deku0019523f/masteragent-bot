"""
cogs/tickets.py
Ticket system lifecycle. The interactive parts live in views/ticket_view.py
(persistent views); this cog wires them into the bot and re-registers them
on startup so buttons keep working after a restart.
"""
from __future__ import annotations

import discord
from discord.ext import commands

from views.ticket_view import TicketCategoryView, TicketControlView, TicketPanelView


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Persistent views must be registered once; discord.py will route
        # component interactions by custom_id even after a restart.
        self.bot.add_view(TicketPanelView(self.bot))
        self.bot.add_view(TicketCategoryView(self.bot))
        self.bot.add_view(TicketControlView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
