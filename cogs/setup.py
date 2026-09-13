"""
cogs/setup.py
/setup — builds (idempotently) the full Master Agent server structure:
roles, categories, channels, and permissions. Also /reset for controlled teardown.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import SERVER_BLUEPRINT, settings
from utils import checks, embeds, permissions, rules_message
from views.confirmation_view import ConfirmationView

logger = logging.getLogger("masteragent.cogs.setup")


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------------------------------------------------------
    # /setup
    # ---------------------------------------------------------------

    @app_commands.command(name="setup", description="Installe automatiquement la structure du serveur Master Agent.")
    @checks.is_owner_or_admin()
    @app_commands.guild_only()
    async def setup_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True, thinking=True)

        missing = permissions.missing_bot_permissions(guild)
        if missing:
            return await interaction.followup.send(
                embed=embeds.error(
                    "Permissions insuffisantes",
                    "Le bot a besoin des permissions suivantes : " + ", ".join(missing),
                ),
                ephemeral=True,
            )

        db = self.bot.db
        await db.ensure_guild(guild.id)
        config = await db.get_guild_config(guild.id)

        progress_lines: list[str] = []
        msg = await interaction.followup.send(
            embed=embeds.info("🔧 Installation Master Agent", "Démarrage de l'installation..."),
            ephemeral=True,
        )

        async def update_progress(line: str):
            progress_lines.append(f"✅ {line}")
            await msg.edit(embed=embeds.info("🔧 Installation Master Agent", "\n".join(progress_lines)))

        # 1. Roles
        role_map: dict[str, discord.Role] = {}
        for role_def in SERVER_BLUEPRINT["roles"]:
            existing_id = await db.get_resource(guild.id, "role", role_def["name"])
            role_obj = guild.get_role(existing_id) if existing_id else None
            if role_obj is None:
                role_obj = discord.utils.get(guild.roles, name=role_def["name"])
            if role_obj is None:
                perms = discord.Permissions(administrator=True) if role_def["admin"] else discord.Permissions.none()
                role_obj = await guild.create_role(
                    name=role_def["name"],
                    colour=discord.Colour(role_def["color"]),
                    hoist=role_def["hoist"],
                    mentionable=role_def["mentionable"],
                    permissions=perms,
                    reason="Master Agent /setup",
                )
            await db.save_resource(guild.id, "role", role_def["name"], role_obj.id)
            role_map[role_def["name"]] = role_obj
        await update_progress("Vérification des permissions")
        await update_progress("Création des rôles")

        # Ensure bot's own top role sits above roles it must manage (best-effort notice only;
        # Discord doesn't let a bot move its own top role above others automatically).
        bot_role = guild.me.top_role
        unmanageable = [r for r in role_map.values() if r >= bot_role and r.name != "⚙️ Bot"]
        if unmanageable:
            logger.warning(
                "Le rôle du bot est trop bas pour gérer: %s", [r.name for r in unmanageable]
            )

        # 2. Categories & channels
        staff_role_ids = [role_map["🛡️ Administrateur"].id, role_map["🔨 Modérateur"].id, role_map["👑 Fondateur"].id]
        everyone = guild.default_role
        staff_category_id = None
        welcome_channel_id = rules_channel_id = logs_channel_id = support_channel_id = None
        moderation_channel_id = announcements_channel_id = None

        for cat_def in SERVER_BLUEPRINT["categories"]:
            existing_cat_id = await db.get_resource(guild.id, "category", cat_def["name"])
            category_obj = guild.get_channel(existing_cat_id) if existing_cat_id else None
            if category_obj is None:
                category_obj = discord.utils.get(guild.categories, name=cat_def["name"])
            if category_obj is None:
                overwrites = {}
                if cat_def["name"] == "🛡️ STAFF":
                    overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
                    for rid in staff_role_ids:
                        overwrites[guild.get_role(rid)] = discord.PermissionOverwrite(view_channel=True)
                category_obj = await guild.create_category(
                    cat_def["name"], overwrites=overwrites, reason="Master Agent /setup"
                )
            await db.save_resource(guild.id, "category", cat_def["name"], category_obj.id)
            if cat_def["name"] == "🛡️ STAFF":
                staff_category_id = category_obj.id

            for chan_def in cat_def["channels"]:
                existing_chan_id = await db.get_resource(guild.id, "channel", chan_def["name"])
                chan_obj = guild.get_channel(existing_chan_id) if existing_chan_id else None
                if chan_obj is None:
                    chan_obj = discord.utils.get(category_obj.channels, name=self._safe_name(chan_def))

                if chan_obj is None:
                    overwrites = self._build_channel_overwrites(guild, chan_def, staff_role_ids, everyone)
                    if chan_def["type"] == "voice":
                        chan_obj = await guild.create_voice_channel(
                            chan_def["name"], category=category_obj, overwrites=overwrites,
                            reason="Master Agent /setup",
                        )
                    else:
                        chan_obj = await guild.create_text_channel(
                            chan_def["name"], category=category_obj, overwrites=overwrites,
                            reason="Master Agent /setup",
                        )
                await db.save_resource(guild.id, "channel", chan_def["name"], chan_obj.id)

                if chan_def["name"] == "👋・bienvenue":
                    welcome_channel_id = chan_obj.id
                elif chan_def["name"] == "📜・reglement":
                    rules_channel_id = chan_obj.id
                elif chan_def["name"] == "📋・logs":
                    logs_channel_id = chan_obj.id
                elif chan_def["name"] == "🎫・support":
                    support_channel_id = chan_obj.id
                elif chan_def["name"] == "🚨・moderation":
                    moderation_channel_id = chan_obj.id
                elif chan_def["name"] == "📣・annonces":
                    announcements_channel_id = chan_obj.id

        await update_progress("Création des catégories")
        await update_progress("Création des salons")
        await update_progress("Configuration des permissions")

        # 3. Save configuration
        await db.update_guild_config(
            guild.id,
            setup_status="completed",
            welcome_channel=welcome_channel_id,
            rules_channel=rules_channel_id,
            logs_channel=logs_channel_id,
            support_channel=support_channel_id,
            moderation_channel=moderation_channel_id,
            announcements_channel=announcements_channel_id,
            staff_category=staff_category_id,
            member_role=role_map["⭐ Membre vérifié"].id,
            new_member_role=role_map["🌱 Nouveau membre"].id,
            admin_role=role_map["🛡️ Administrateur"].id,
            moderator_role=role_map["🔨 Modérateur"].id,
            founder_role=role_map["👑 Fondateur"].id,
            bot_role=role_map["⚙️ Bot"].id,
            welcome_enabled=int(settings.DEFAULT_WELCOME_ENABLED),
            tickets_enabled=int(settings.DEFAULT_TICKETS_ENABLED),
            projects_enabled=int(settings.DEFAULT_PROJECTS_ENABLED),
            voice_enabled=int(settings.DEFAULT_VOICE_ENABLED),
        )
        await update_progress("Initialisation de la base de données")

        # 4. Post rules acceptance panel + ticket panel
        from views.ticket_view import TicketPanelView

        rules_channel = guild.get_channel(rules_channel_id)
        if rules_channel:
            # Réutilise le texte déjà personnalisé via /reglement definir s'il existe,
            # sinon le règlement par défaut. sync_rules_panel est idempotent : il édite
            # le panneau déjà posté au lieu d'en reposter un nouveau.
            rules_text = config["rules_text"] if config and config["rules_text"] else settings.DEFAULT_RULES_TEXT
            await rules_message.sync_rules_panel(self.bot, guild, rules_channel, rules_text)

        support_channel = guild.get_channel(support_channel_id)
        if support_channel:
            already_posted = False
            async for m in support_channel.history(limit=20):
                if m.author == guild.me and m.components:
                    already_posted = True
                    break
            if not already_posted:
                await support_channel.send(
                    embed=embeds.info(
                        "🎫 Support Master Agent",
                        "Besoin d'aide, envie de collaborer, ou de signaler un problème ? "
                        "Cliquez ci-dessous pour ouvrir un ticket privé avec le staff.",
                    ),
                    view=TicketPanelView(self.bot),
                )

        final_embed = embeds.success(
            "Installation terminée",
            "🎉 Le serveur Master Agent est configuré !\n\n" + "\n".join(progress_lines),
        )
        await msg.edit(embed=final_embed)

    def _safe_name(self, chan_def: dict) -> str:
        return chan_def["name"]

    def _build_channel_overwrites(self, guild, chan_def, staff_role_ids, everyone):
        overwrites = {}
        if chan_def.get("read_only"):
            overwrites[everyone] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
            for rid in staff_role_ids:
                role = guild.get_role(rid)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(send_messages=True)
        if chan_def.get("staff_only"):
            overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
            for rid in staff_role_ids:
                role = guild.get_role(rid)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        return overwrites

    # ---------------------------------------------------------------
    # /reset
    # ---------------------------------------------------------------

    reset_group = app_commands.Group(name="reset", description="Réinitialise la configuration Master Agent.")

    @reset_group.command(name="config", description="Réinitialise uniquement la configuration enregistrée (pas les salons).")
    @checks.is_owner_or_admin()
    async def reset_config(self, interaction: discord.Interaction):
        view = ConfirmationView(author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=embeds.warning(
                "Confirmer la réinitialisation",
                "Cela va effacer la configuration enregistrée (rôles/salons liés en base). "
                "Aucun salon ou rôle Discord ne sera supprimé. Continuer ?",
            ),
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.confirmed:
            return await interaction.edit_original_response(
                embed=embeds.info("Annulé", "Aucune modification effectuée."), view=None
            )

        db = self.bot.db
        await db.execute("DELETE FROM server_resources WHERE guild_id=?", (interaction.guild.id,))
        await db.update_guild_config(interaction.guild.id, setup_status="not_started")
        await interaction.edit_original_response(
            embed=embeds.success("Configuration réinitialisée", "Vous pouvez relancer /setup."), view=None
        )

    @reset_group.command(name="masteragent", description="⚠️ Réinitialisation complète (destructeur, confirmations multiples).")
    @checks.is_owner_or_admin()
    async def reset_masteragent(self, interaction: discord.Interaction):
        view1 = ConfirmationView(author_id=interaction.user.id)
        await interaction.response.send_message(
            embed=embeds.error(
                "⚠️ RÉINITIALISATION COMPLÈTE",
                "Ceci va supprimer TOUTES les données Master Agent enregistrées pour ce serveur "
                "(config, tickets, warnings, agents...). Les salons/rôles Discord créés par le bot "
                "ne seront PAS supprimés automatiquement — vous devrez le faire manuellement si besoin.\n\n"
                "**Cette action est irréversible.** Confirmez une première fois pour continuer.",
            ),
            view=view1,
            ephemeral=True,
        )
        await view1.wait()
        if not view1.confirmed:
            return await interaction.edit_original_response(embed=embeds.info("Annulé", ""), view=None)

        view2 = ConfirmationView(author_id=interaction.user.id)
        await interaction.edit_original_response(
            embed=embeds.error(
                "⚠️ DERNIÈRE CONFIRMATION",
                "Êtes-vous ABSOLUMENT certain ? Toutes les données seront perdues définitivement.",
            ),
            view=view2,
        )
        await view2.wait()
        if not view2.confirmed:
            return await interaction.edit_original_response(embed=embeds.info("Annulé", ""), view=None)

        db = self.bot.db
        guild_id = interaction.guild.id
        for table in [
            "server_resources", "members", "profiles", "warnings", "moderation_logs",
            "tickets", "projects", "staff_actions", "staff_members",
        ]:
            await db.execute(f"DELETE FROM {table} WHERE guild_id=?", (guild_id,))
        await db.execute("DELETE FROM guilds WHERE guild_id=?", (guild_id,))

        await interaction.edit_original_response(
            embed=embeds.success("Réinitialisation terminée", "Toutes les données ont été effacées."), view=None
        )


async def setup(bot: commands.Bot):
    # Note: reset_group is a class-level app_commands.Group attribute, so
    # discord.py automatically registers it (and its subcommands) with the
    # CommandTree when the cog is added — no manual tree.add_command needed.
    await bot.add_cog(SetupCog(bot))
