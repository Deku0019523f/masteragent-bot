"""
views/project_view.py
Modal form for the /agent command — présentation d'un agent IA créé sur
Master Agent. Réutilise le schéma "projects" en base (technologies →
intégrations, github/demo → liens, collaborators → recherche de retours).
"""
from __future__ import annotations

import discord

from utils import embeds


class ProjectModal(discord.ui.Modal, title="🤖 Présenter mon agent"):
    name = discord.ui.TextInput(label="Nom de l'agent", max_length=100, required=True)
    description = discord.ui.TextInput(
        label="Cas d'usage / description", style=discord.TextStyle.paragraph, max_length=1000, required=True
    )
    technologies = discord.ui.TextInput(
        label="Intégrations utilisées",
        placeholder="WhatsApp Business API, CRM, paiement...",
        max_length=200,
        required=False,
    )
    links = discord.ui.TextInput(
        label="Lien documentation / démo (séparés par une virgule)",
        placeholder="https://..., https://demo.example.com",
        max_length=300,
        required=False,
    )
    collaborators = discord.ui.TextInput(
        label="Ouvert aux retours de la communauté ? (oui/non)", max_length=10, required=False
    )

    def __init__(self, bot, target_channel: discord.TextChannel):
        super().__init__()
        self.bot = bot
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        doc_link, demo_link = "", ""
        if self.links.value:
            parts = [p.strip() for p in self.links.value.split(",")]
            doc_link = parts[0] if len(parts) > 0 else ""
            demo_link = parts[1] if len(parts) > 1 else ""

        seeking_feedback = self.collaborators.value.strip().lower() in {"oui", "yes", "o", "y"}

        db = self.bot.db
        project_id = await db.create_project(
            interaction.guild.id,
            interaction.user.id,
            self.name.value,
            self.description.value,
            self.technologies.value or "",
            doc_link,
            demo_link,
            seeking_feedback,
        )

        embed = embeds.project_embed(
            interaction.user,
            self.name.value,
            self.description.value,
            self.technologies.value or "",
            doc_link,
            demo_link,
            seeking_feedback,
        )

        message = await self.target_channel.send(embed=embed)
        await db.set_project_message(project_id, message.id, self.target_channel.id)

        await interaction.response.send_message(
            f"✅ Agent publié dans {self.target_channel.mention} !", ephemeral=True
        )
