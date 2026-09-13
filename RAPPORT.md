# RAPPORT.md — Master Agent (bot Discord communauté)

> Ce fichier sert de mémoire de projet. À mettre à jour après chaque étape importante.

## Objectif du projet

Bot Discord professionnel pour la communauté officielle **Master Agent**, une plateforme de création d'agents IA pour l'automatisation WhatsApp (service client, présentation produits, suivi des ventes). Le bot installe et administre automatiquement la structure du serveur (rôles, catégories, salons), gère l'accueil, la modération, les tickets, la présentation d'agents et les profils membres.

**Historique** : ce projet a démarré sous le nom "AfroCodeurs" (communauté VibeCoding/dev) puis a été entièrement rebrandé le 13/09/2026 pour devenir "Master Agent", avec changement de public cible (clients/utilisateurs de la plateforme Master Agent, plus VibeCodeurs génériques).

Périmètre strict : uniquement le bot Discord et la communauté. Aucune API, aucune intégration web, aucune synchronisation avec l'application Master Agent elle-même.

## Stack et technologies

- Python 3.11+
- discord.py 2.x (>=2.4.0,<3.0.0)
- aiosqlite (SQLite async)
- python-dotenv
- systemd (déploiement VPS Ubuntu)

## Architecture et structure des fichiers

```
masteragent/
├── bot.py                    # Entrypoint : chargement config/db/cogs, sync des slash commands
├── config.py                  # Settings (.env) + SERVER_BLUEPRINT (rôles/catégories/salons)
├── requirements.txt / requirements-dev.txt
├── .env.example / .gitignore
├── masteragent.service        # Unit systemd
├── cogs/
│   ├── setup.py                # /setup (idempotent), /reset config, /reset masteragent
│   ├── welcome.py              # on_member_join / on_member_remove
│   ├── moderation.py           # /warn /warnings /clear /timeout /untimeout /kick /ban /unban /lock /unlock
│   ├── administration.py       # /role add|remove|info|list, /config
│   ├── tickets.py              # enregistre les persistent views tickets au démarrage
│   ├── projects.py             # /agent (présentation d'un agent IA)
│   ├── member.py               # /profile /userinfo /serverinfo /members
│   ├── staff.py                # /staff list|add|remove|promote|demote
│   └── utility.py              # /ping /about /rules /stats /help
├── database/
│   ├── models.py                # DDL SQLite (9 tables + index)
│   └── database.py               # Couche d'accès asynchrone (verrou asyncio + WAL)
├── views/
│   ├── welcome_view.py           # bouton persistant "J'accepte le règlement"
│   ├── ticket_view.py            # panneau ticket + menu catégories + contrôles (claim/close/delete)
│   ├── project_view.py           # modal /agent (nom, cas d'usage, intégrations, liens, retours)
│   └── confirmation_view.py      # confirmation générique (utilisée par /reset)
├── utils/
│   ├── permissions.py            # is_hierarchy_safe, bot_can_act_on, can_assign_role
│   ├── embeds.py                  # builders d'embeds centralisés (couleurs, footer commun)
│   ├── checks.py                  # is_owner_or_admin(), has_staff_role(), guild_configured()
│   ├── logger.py                  # logging fichier (rotatif) + console
│   └── helpers.py                 # parse_duration/format_duration, etc.
└── tests/                          # tests sans token Discord (SQLite + hiérarchie + helpers)
```

## Fonctionnalités développées

- `/setup` idempotent : crée rôles/catégories/salons, détecte l'existant, ne duplique/supprime jamais, sauvegarde tous les IDs en SQLite (`server_resources`), poste le panneau règlement + panneau tickets.
- Structure serveur Master Agent : catégories INFORMATIONS, COMMUNAUTÉ, AGENTS IA, RESSOURCES, SUPPORT, VOCAL, STAFF. Rôles : Fondateur, Administrateur, Modérateur, Responsable Communauté, Expert Automatisation, Créateur d'agents, Client Pro, Membre vérifié, Nouveau membre, Bot.
- Accueil automatique + acceptation du règlement par bouton persistant (survit aux redémarrages).
- Modération complète avec hiérarchie de rôles vérifiée avant toute action sensible (`utils/permissions.py`), auto-sanction sur seuils de warnings configurables.
- Tickets par panneau à bouton + menu catégories, salons privés, claim/close/delete, logs.
- `/agent` : formulaire modal de présentation d'un agent IA (nom, cas d'usage, intégrations, liens doc/démo, ouverture aux retours) → embed publié dans `🚀・mes-agents`.
- Profils membres (`/profile`), infos serveur/membre, stats.
- `/config` pour activer/désactiver les modules (accueil, tickets, agents, vocal temporaire).
- `/reset config` et `/reset masteragent` avec confirmations multiples, jamais de suppression silencieuse.
- Logs applicatifs (fichier rotatif + console) et logs Discord (`#logs`, `#moderation`).

## Fonctionnalités restantes / non implémentées

- Salons vocaux temporaires (création/suppression auto) : le flag `voice_enabled` existe en base et dans `/config`, mais la logique de création/suppression automatique des salons vocaux temporaires n'est **pas encore codée** (mentionnée comme optionnelle dans le cahier des charges initial).
- Auto-déclenchement de sanction "majeure" au seuil de 5 warnings : actuellement seulement un message d'alerte est envoyé dans les logs, pas d'action automatique concrète (volontaire — laissé à la décision manuelle du staff).

## Modifications importantes effectuées

- **13/09/2026 — Rebranding complet AfroCodeurs → Master Agent** :
  - `SERVER_BLUEPRINT` (config.py) entièrement revu : nouveaux rôles (Expert Automatisation, Créateur d'agents, Client Pro), nouvelles catégories (AGENTS IA remplace VIBECODING, RESSOURCES remplace COLLABORATION), nouveaux salons (`🚀・mes-agents`, `💬・whatsapp-business`, `📖・documentation`, etc.)
  - Rôle Bot : emoji changé de 🤖 à ⚙️ pour éviter le conflit avec le nouveau rôle 🤖 Créateur d'agents.
  - Commande `/projet` renommée `/agent` (cog `cogs/projects.py`, vue `views/project_view.py`) : champs adaptés (nom de l'agent, cas d'usage, intégrations, liens documentation/démo).
  - `embeds.project_embed()` adapté (icône 🤖, "Intégrations" au lieu de "Technologies", "Documentation" au lieu de "GitHub").
  - Tous les textes visibles (bienvenue, /about, /setup, titres d'embeds, footer) mis à jour.
  - Fichier systemd renommé `afrocodeurs.service` → `masteragent.service`.
  - **Bug corrigé pendant le rebranding** : un remplacement global "AfroCodeurs"→"Master Agent" avait cassé un identifiant Python (`class AfroCodeursBot` → `class Master AgentBot`, espace invalide). Corrigé en `MasterAgentBot`. Tous les fichiers ont été recompilés (`py_compile`) après coup pour confirmer qu'aucune autre casse similaire n'était survenue.

## Problèmes rencontrés et solutions

- **Registration en double des `app_commands.Group`** : un premier jet appelait `bot.tree.add_command(cog.reset_group)` après `bot.add_cog(cog)`, alors que discord.py enregistre déjà automatiquement les `Group` définis comme attributs de classe lors de `add_cog()`. Corrigé en retirant les appels manuels dans `cogs/setup.py`, `cogs/administration.py`, `cogs/staff.py`.
- **`member.ban(delete_message_days=...)`** est déprécié depuis discord.py 2.3 → utilisé `delete_message_seconds=0` à la place.
- **Environnement sandbox sans accès réseau** : impossible d'installer discord.py/aiosqlite/pytest ou de pousser sur GitHub depuis cet environnement (confirmé par un test `curl` direct → 403 "Host not in allowlist"). Toute opération réseau (git push, pip install réel, tests pytest réels) doit être faite par l'utilisateur en local ou via Claude Code.

## Dépendances installées

Voir `requirements.txt` :
```
discord.py>=2.4.0,<3.0.0
aiosqlite>=0.20.0
python-dotenv>=1.0.1
```
Dev/tests (`requirements-dev.txt`) : `pytest>=8.0.0`, `pytest-asyncio>=0.24.0`.

## Commandes importantes

```bash
# Installation
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis éditer DISCORD_TOKEN

# Lancement local
python bot.py

# Tests (nécessite pip install -r requirements-dev.txt)
pytest

# Déploiement VPS — voir README.md section "Déploiement VPS (systemd)"
sudo systemctl enable masteragent
sudo systemctl start masteragent
sudo journalctl -u masteragent -f
```

## Variables d'environnement nécessaires

(voir `.env.example` — aucune valeur secrète n'est stockée ici)

- `DISCORD_TOKEN` — token du bot Discord
- `OWNER_IDS` — IDs Discord des propriétaires (optionnel)
- `COMMAND_PREFIX` — préfixe texte (bot fonctionne principalement en slash commands)
- `LOG_LEVEL` — DEBUG/INFO/WARNING/ERROR
- `DATABASE_PATH` — chemin du fichier SQLite
- `DEFAULT_WELCOME_ENABLED`, `DEFAULT_TICKETS_ENABLED`, `DEFAULT_PROJECTS_ENABLED`, `DEFAULT_VOICE_ENABLED` — valeurs par défaut appliquées lors de `/setup`

## État actuel du projet

- Base de code complète et cohérente pour le rebranding Master Agent : les 29 fichiers Python compilent sans erreur (`py_compile`), tous les rôles/salons référencés dans le code existent dans `SERVER_BLUEPRINT` (vérifié par script).
- **Non exécuté réellement** : les tests pytest et le bot lui-même n'ont pas pu tourner dans cet environnement (pas d'accès réseau pour installer les dépendances). À valider en local avant déploiement.
- Le projet n'est **pas encore poussé sur un dépôt GitHub** — cet environnement n'a pas d'accès réseau sortant vers GitHub (confirmé, bloqué au niveau infrastructure). L'utilisateur doit pousser lui-même en local, ou utiliser Claude Code qui a un accès réseau réel.
- Fichier livré sous forme de zip via `present_files` à chaque itération.

## Prochaines étapes à réaliser

1. L'utilisateur récupère le zip, l'extrait en local, installe les dépendances (`pip install -r requirements.txt`).
2. Configure `.env` avec un vrai token Discord (créer l'app sur discord.com/developers/applications).
3. Lance `python bot.py` en local pour valider que tout fonctionne, exécute `/setup` sur un serveur de test.
4. Lance `pytest` (après `pip install -r requirements-dev.txt`) pour valider la couche base de données/permissions.
5. Pousse le code sur son dépôt GitHub (en local ou via Claude Code — pas possible depuis ce chat).
6. Décider si les salons vocaux temporaires (fonctionnalité optionnelle non codée) sont nécessaires ; si oui, à implémenter dans un futur cog `voice.py`.
7. Déploiement VPS via `masteragent.service` (voir README.md).
