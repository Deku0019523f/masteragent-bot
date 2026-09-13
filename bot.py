"""
bot.py
Master Agent — entrypoint. Loads config, sets up logging and the database,
loads all cogs, re-registers persistent views, and starts the bot.
"""
from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from database.database import Database
from utils.logger import setup_logging

INITIAL_EXTENSIONS = [
    "cogs.setup",
    "cogs.welcome",
    "cogs.moderation",
    "cogs.administration",
    "cogs.customization",
    "cogs.tickets",
    "cogs.projects",
    "cogs.member",
    "cogs.staff",
    "cogs.utility",
]

logger = setup_logging(settings.LOG_DIR, settings.LOG_LEVEL)


class MasterAgentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = False  # not needed: bot is slash-command only
        super().__init__(command_prefix=settings.COMMAND_PREFIX, intents=intents, help_command=None)
        self.db = Database(settings.DATABASE_PATH)

    async def setup_hook(self) -> None:
        await self.db.connect()

        for ext in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(ext)
                logger.info("Extension chargée: %s", ext)
            except Exception:
                logger.exception("Échec du chargement de l'extension %s", ext)

        # Re-register persistent views so buttons keep working after a restart.
        from views.welcome_view import RulesAcceptView
        self.add_view(RulesAcceptView(self))

        try:
            synced = await self.tree.sync()
            logger.info("Commandes synchronisées: %d", len(synced))
        except discord.HTTPException:
            # Un raté ici (rate limit, hoquet réseau côté Discord) ne doit pas tuer
            # tout le process : les commandes déjà enregistrées côté Discord restent
            # fonctionnelles même sans nouvelle synchronisation.
            logger.exception(
                "Échec de la synchronisation des commandes (tree.sync) — le bot démarre "
                "quand même avec les commandes déjà enregistrées côté Discord."
            )

    async def on_ready(self):
        logger.info("Connecté en tant que %s (ID: %s)", self.user, self.user.id)
        logger.info("Présent sur %d serveur(s)", len(self.guilds))
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="la communauté Master Agent 🚀")
        )

    async def on_disconnect(self):
        logger.warning("Bot déconnecté de Discord.")

    async def close(self):
        logger.info("Arrêt du bot en cours...")
        await self.db.close()
        await super().close()


bot = MasterAgentBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    from utils import checks, embeds

    if isinstance(error, app_commands.CommandOnCooldown):
        message = f"⏳ Patientez encore {error.retry_after:.1f}s avant de réutiliser cette commande."
    elif isinstance(error, app_commands.MissingPermissions):
        message = "❌ Vous n'avez pas la permission d'utiliser cette commande."
    elif isinstance(error, app_commands.NoPrivateMessage):
        message = "❌ Cette commande doit être utilisée dans un serveur."
    elif isinstance(error, (checks.InsufficientRole, checks.NotConfigured)):
        message = f"❌ {error}"
    elif isinstance(error, discord.Forbidden):
        message = "❌ Je n'ai pas les permissions nécessaires pour effectuer cette action."
    else:
        logger.exception("Erreur de commande non gérée", exc_info=error)
        message = "❌ Une erreur inattendue est survenue. Le staff a été notifié dans les logs."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


def main():
    settings.validate()
    bot.run(settings.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
