"""
config.py
Centralized configuration loaded from environment variables (.env).
Never hardcode secrets here — everything sensitive comes from the environment.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings for the Master Agent community bot."""

    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")
    OWNER_IDS: list[int] = [
        int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip().isdigit()
    ]
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "masteragent.db"))
    LOG_DIR: Path = BASE_DIR / "logs"

    # Feature toggles usable as sane defaults during /setup
    DEFAULT_WELCOME_ENABLED: bool = _get_bool("DEFAULT_WELCOME_ENABLED", True)
    DEFAULT_TICKETS_ENABLED: bool = _get_bool("DEFAULT_TICKETS_ENABLED", True)
    DEFAULT_PROJECTS_ENABLED: bool = _get_bool("DEFAULT_PROJECTS_ENABLED", True)
    DEFAULT_VOICE_ENABLED: bool = _get_bool("DEFAULT_VOICE_ENABLED", False)

    # Contenu par défaut, personnalisable par serveur via /reglement et /bienvenue
    # (stocké en base dans guilds.rules_text / guilds.welcome_message une fois modifié).
    DEFAULT_RULES_TEXT: str = (
        "**Bienvenue sur le règlement de Master Agent !**\n\n"
        "1️⃣ **Respect** — Aucune insulte, harcèlement ou discrimination envers un membre.\n"
        "2️⃣ **Pas de spam** — Pas de publicité, liens d'affiliation ou démarchage sans autorisation du staff.\n"
        "3️⃣ **Contenu adapté** — Pas de contenu NSFW, violent ou illégal.\n"
        "4️⃣ **Bon usage des salons** — Restez dans le sujet de chaque salon.\n"
        "5️⃣ **Respect du staff** — Les décisions de modération se contestent en ticket, pas publiquement.\n\n"
        "Le non-respect de ce règlement peut entraîner un avertissement, une exclusion temporaire ou un bannissement.\n\n"
        "Cliquez sur le bouton ci-dessous pour l'accepter et débloquer l'accès complet au serveur."
    )

    DEFAULT_WELCOME_MESSAGE: str = (
        "Ravi de t'accueillir sur **Master Agent**, {member_mention} !\n\n"
        "Pour commencer :\n"
        "1️⃣ Lis le règlement dans {rules_channel} et clique sur *J'accepte le règlement*\n"
        "2️⃣ Présente-toi dans le salon dédié\n"
        "3️⃣ Découvre les salons Agents IA et rejoins la communauté 🚀"
    )

    @classmethod
    def validate(cls) -> None:
        if not cls.DISCORD_TOKEN:
            raise RuntimeError(
                "DISCORD_TOKEN manquant. Copiez .env.example vers .env et renseignez votre token."
            )


settings = Settings()

# Server structure blueprint used by the /setup command.
# Kept here (not hardcoded inside cogs) so it can be reviewed/edited in one place.
# Adapted for the Master Agent community (clients/utilisateurs de la plateforme
# de création d'agents IA pour l'automatisation WhatsApp).
SERVER_BLUEPRINT = {
    "roles": [
        # name, color_hex, hoist, mentionable, permissions_admin(bool)
        {"name": "👑 Fondateur", "color": 0xE74C3C, "hoist": True, "mentionable": True, "admin": True},
        {"name": "🛡️ Administrateur", "color": 0xE67E22, "hoist": True, "mentionable": True, "admin": True},
        {"name": "🔨 Modérateur", "color": 0xF1C40F, "hoist": True, "mentionable": True, "admin": False},
        {"name": "🤝 Responsable Communauté", "color": 0x1ABC9C, "hoist": True, "mentionable": True, "admin": False},
        {"name": "🎓 Expert Automatisation", "color": 0x3498DB, "hoist": True, "mentionable": True, "admin": False},
        {"name": "🤖 Créateur d'agents", "color": 0x9B59B6, "hoist": False, "mentionable": False, "admin": False},
        {"name": "💼 Client Pro", "color": 0x2ECC71, "hoist": False, "mentionable": False, "admin": False},
        {"name": "⭐ Membre vérifié", "color": 0x95A5A6, "hoist": False, "mentionable": False, "admin": False},
        {"name": "🌱 Nouveau membre", "color": 0x7F8C8D, "hoist": False, "mentionable": False, "admin": False},
        {"name": "⚙️ Bot", "color": 0x34495E, "hoist": True, "mentionable": False, "admin": False},
    ],
    "categories": [
        {
            "name": "📢 INFORMATIONS",
            "channels": [
                {"name": "📣・annonces", "type": "text", "read_only": True},
                {"name": "👋・bienvenue", "type": "text", "read_only": True},
                {"name": "📜・reglement", "type": "text", "read_only": True},
                {"name": "📌・informations", "type": "text", "read_only": True},
                {"name": "🔗・masteragent", "type": "text", "read_only": True},
            ],
        },
        {
            "name": "💬 COMMUNAUTÉ",
            "channels": [
                {"name": "💬・general", "type": "text"},
                {"name": "👋・presentations", "type": "text"},
                {"name": "🤝・entraide", "type": "text"},
                {"name": "💡・idees-suggestions", "type": "text"},
                {"name": "🎯・cas-usage", "type": "text"},
            ],
        },
        {
            "name": "🤖 AGENTS IA",
            "channels": [
                {"name": "🚀・mes-agents", "type": "text"},
                {"name": "🔥・automatisations-avancees", "type": "text"},
                {"name": "🧪・experimentations", "type": "text"},
                {"name": "📚・tutoriels", "type": "text"},
                {"name": "🛠️・outils-integrations", "type": "text"},
                {"name": "💬・whatsapp-business", "type": "text"},
            ],
        },
        {
            "name": "📚 RESSOURCES",
            "channels": [
                {"name": "📖・documentation", "type": "text", "read_only": True},
                {"name": "❓・faq", "type": "text"},
                {"name": "📰・changelog", "type": "text", "read_only": True},
                {"name": "💡・bonnes-pratiques", "type": "text"},
            ],
        },
        {
            "name": "🎫 SUPPORT",
            "channels": [
                {"name": "🎫・support", "type": "text"},
                {"name": "🐛・bugs-signalements", "type": "text"},
            ],
        },
        {
            "name": "🔊 VOCAL",
            "channels": [
                {"name": "🎙️・Discussion", "type": "voice"},
                {"name": "👥・Réunion de groupe", "type": "voice"},
                {"name": "🔒・Réunion privée", "type": "voice"},
                {"name": "🎮・Pause", "type": "voice"},
            ],
        },
        {
            "name": "🛡️ STAFF",
            "channels": [
                {"name": "📋・logs", "type": "text", "staff_only": True},
                {"name": "🚨・moderation", "type": "text", "staff_only": True},
                {"name": "🎫・tickets-staff", "type": "text", "staff_only": True},
                {"name": "🛠️・staff", "type": "text", "staff_only": True},
            ],
        },
    ],
}
