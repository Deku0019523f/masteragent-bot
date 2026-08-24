# AfroCodeurs — Bot Discord

Bot Discord professionnel pour la communauté **AfroCodeurs**, dédiée aux VibeCodeurs, développeurs, créateurs de projets numériques, étudiants, entrepreneurs tech, designers et makers.

Le bot installe et administre automatiquement la structure complète du serveur : rôles, catégories, salons, accueil, règlement, tickets, modération, projets et profils.

> ⚠️ Ce projet gère uniquement le bot Discord et la communauté. Aucune intégration web, aucune API, aucune synchronisation avec AfroCodeurs.org.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Création du bot Discord](#création-du-bot-discord)
- [Installation locale](#installation-locale)
- [Configuration](#configuration)
- [Invitation du bot](#invitation-du-bot)
- [Lancement](#lancement)
- [Déploiement VPS (systemd)](#déploiement-vps-systemd)
- [Liste des commandes](#liste-des-commandes)
- [Dépannage](#dépannage)
- [Sécurité](#sécurité)
- [Tests](#tests)

---

## Fonctionnalités

- **`/setup`** : construit automatiquement rôles, catégories et salons (idempotent — ne duplique jamais, ne supprime jamais un salon existant non géré).
- **Accueil automatique** : rôle "Nouveau membre", message de bienvenue, parcours vers le règlement.
- **Règlement à bouton** : acceptation persistante (survit aux redémarrages), attribue "Membre vérifié".
- **Modération complète** : `/warn`, `/warnings`, `/clear`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/unban`, `/lock`, `/unlock`, avec seuils d'auto-sanction configurables.
- **Gestion des rôles** sécurisée par hiérarchie (`/role add|remove|info|list`).
- **Système de staff** : roster, promotions, historique (`/staff ...`).
- **Tickets** : panneau à bouton, catégories, salons privés, prise en charge, fermeture, logs.
- **Projets** : formulaire modal (`/projet`) générant un embed professionnel.
- **Profils membres** : `/profile` (configuration + affichage public).
- **Commandes utilitaires** : `/ping`, `/help`, `/about`, `/rules`, `/stats`, `/userinfo`, `/serverinfo`, `/members`.
- **`/reset config`** et **`/reset afrocodeurs`** : réinitialisation contrôlée avec confirmations.
- Logs applicatifs (fichier + console) et logs Discord dans `#logs` / `#moderation`.

## Architecture

```
afrocodeurs/
├── bot.py                  # Point d'entrée
├── config.py                # Configuration + blueprint de structure serveur
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── afrocodeurs.service      # Unit systemd
├── cogs/                    # Commandes slash & listeners
│   ├── setup.py
│   ├── welcome.py
│   ├── moderation.py
│   ├── administration.py
│   ├── tickets.py
│   ├── projects.py
│   ├── member.py
│   ├── staff.py
│   └── utility.py
├── database/
│   ├── database.py           # Couche d'accès asynchrone (aiosqlite)
│   └── models.py              # Schéma SQL
├── views/                     # Boutons/menus/formulaires persistants
│   ├── welcome_view.py
│   ├── ticket_view.py
│   ├── project_view.py
│   └── confirmation_view.py
├── utils/
│   ├── permissions.py         # Sécurité hiérarchie des rôles
│   ├── embeds.py               # Embeds centralisés
│   ├── logger.py
│   ├── checks.py                # Vérifications de permissions pour slash commands
│   └── helpers.py
├── tests/
└── logs/
```

## Prérequis

- Python 3.11 ou supérieur
- Un serveur Discord où vous êtes propriétaire ou administrateur
- Une application Discord + bot (voir ci-dessous)
- Un VPS Ubuntu (pour la production)

## Création du bot Discord

1. Rendez-vous sur https://discord.com/developers/applications
2. Créez une nouvelle application, nommez-la **AfroCodeurs**.
3. Dans l'onglet **Bot**, cliquez sur *Add Bot*.
4. Activez l'intent **SERVER MEMBERS INTENT** (obligatoire pour l'accueil automatique).
5. Copiez le **token** du bot (bouton *Reset Token* si besoin) — vous en aurez besoin pour `.env`.
6. Ne partagez jamais ce token publiquement. S'il a été exposé, régénérez-le immédiatement.

### Permissions nécessaires

Lors de l'invitation, cochez au minimum :

- Gérer les rôles (Manage Roles)
- Gérer les salons (Manage Channels)
- Expulser des membres (Kick Members)
- Bannir des membres (Ban Members)
- Modérer des membres (Timeout)
- Gérer les messages (Manage Messages)
- Voir les salons / Envoyer des messages / Intégrer des liens / Lire l'historique

Ou plus simplement, cochez la permission **Administrateur** si votre serveur est un environnement de test.

## Installation locale

```bash
git clone https://github.com/<votre-compte>/AfroCodeurs.git
cd AfroCodeurs
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Éditez `.env` :

```env
DISCORD_TOKEN=votre_token_ici
OWNER_IDS=
COMMAND_PREFIX=!
LOG_LEVEL=INFO
DATABASE_PATH=afrocodeurs.db
DEFAULT_WELCOME_ENABLED=true
DEFAULT_TICKETS_ENABLED=true
DEFAULT_PROJECTS_ENABLED=true
DEFAULT_VOICE_ENABLED=false
```

`.env` est ignoré par git (`.gitignore`) — ne le commitez jamais.

## Invitation du bot

Générez un lien d'invitation depuis l'onglet **OAuth2 > URL Generator** de votre application :

- Scopes : `bot`, `applications.commands`
- Permissions : voir section ci-dessus

Ouvrez le lien, sélectionnez votre serveur, autorisez.

## Lancement

```bash
python bot.py
```

Une fois le bot en ligne, exécutez `/setup` sur votre serveur (propriétaire ou administrateur uniquement) pour construire automatiquement toute la structure.

## Déploiement VPS (systemd)

```bash
# 1. Connexion au VPS et création d'un utilisateur dédié (recommandé)
sudo adduser afrocodeurs
sudo su - afrocodeurs

# 2. Installer Python si nécessaire
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git

# 3. Cloner le projet
git clone https://github.com/<votre-compte>/AfroCodeurs.git
cd AfroCodeurs

# 4. Environnement virtuel + dépendances
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Configuration
cp .env.example .env
nano .env   # renseignez DISCORD_TOKEN et le reste

# 6. Copier le fichier systemd (adapter User/WorkingDirectory si besoin)
sudo cp afrocodeurs.service /etc/systemd/system/afrocodeurs.service
sudo nano /etc/systemd/system/afrocodeurs.service   # vérifiez les chemins

# 7. Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable afrocodeurs
sudo systemctl start afrocodeurs

# 8. Vérifier le statut et les logs
sudo systemctl status afrocodeurs
sudo journalctl -u afrocodeurs -f

# Redémarrer après une mise à jour du code
sudo systemctl restart afrocodeurs
```

## Liste des commandes

### Générales
| Commande | Description |
|---|---|
| `/ping` | Latence du bot |
| `/about` | À propos du bot |
| `/help` | Liste des commandes (adaptée au rôle) |
| `/rules` | Lien vers le règlement |
| `/stats` | Statistiques du serveur |
| `/userinfo [membre]` | Informations sur un membre |
| `/serverinfo` | Informations sur le serveur |
| `/members` | Répartition des membres par rôle |
| `/profile [membre]` | Configurer ou consulter un profil |
| `/projet` | Présenter un projet (formulaire) |

### Modération (staff)
| Commande | Description |
|---|---|
| `/warn @membre raison` | Avertir un membre |
| `/warnings @membre` | Historique des avertissements |
| `/clear montant` | Supprimer des messages |
| `/timeout @membre durée raison` | Timeout (ex: `10m`, `2h`, `1d`) |
| `/untimeout @membre` | Retirer un timeout |
| `/kick @membre raison` | Expulser |
| `/ban @membre raison` | Bannir |
| `/unban id raison` | Débannir |
| `/lock` / `/unlock` | Verrouiller/déverrouiller le salon |

### Administration
| Commande | Description |
|---|---|
| `/setup` | Installer la structure du serveur |
| `/config` | Voir/modifier la configuration |
| `/role add\|remove\|info\|list` | Gestion des rôles |
| `/staff list\|add\|remove\|promote\|demote` | Gestion de l'équipe staff |
| `/reset config` | Réinitialiser la configuration enregistrée |
| `/reset afrocodeurs` | Réinitialisation complète (double confirmation) |

## Dépannage

- **Le bot ne répond à aucune commande slash** : vérifiez que `applications.commands` a bien été coché lors de l'invitation, et attendez quelques minutes après le premier démarrage (synchronisation Discord).
- **"Permissions insuffisantes" lors de `/setup`** : donnez au rôle du bot les permissions listées plus haut, et assurez-vous que son rôle est placé suffisamment haut dans la hiérarchie des rôles du serveur.
- **Les boutons (règlement, tickets) ne répondent plus après un redémarrage** : vérifiez les logs — les vues persistantes sont ré-enregistrées automatiquement dans `setup_hook()`, mais un plantage avant cette étape peut l'empêcher.
- **`database is locked`** : le bot utilise déjà `WAL` et un verrou asyncio pour éviter cela ; si le fichier `.db` a été copié pendant que le bot tournait, redémarrez proprement.
- Consultez toujours `logs/afrocodeurs.log` et `journalctl -u afrocodeurs -f` pour le détail technique des erreurs.

## Sécurité

- Le token n'est jamais lu que depuis `.env` (variable d'environnement), jamais codé en dur, jamais loggé.
- Toute commande sensible vérifie : permissions Discord, rôle, hiérarchie, appartenance au serveur, permissions du bot.
- `/reset` ne supprime jamais silencieusement quoi que ce soit — confirmations explicites obligatoires.
- Le bot ne supprime jamais un salon/rôle qu'il n'a pas lui-même créé et enregistré.
- **Si un token (Discord, GitHub, etc.) a été partagé ou exposé accidentellement, régénérez/révoquez-le immédiatement**, même s'il a une durée de vie limitée.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent : initialisation SQLite, configuration serveur, avertissements, idempotence des ressources (`/setup`), profils, tickets, roster staff, et la logique de hiérarchie des permissions — sans nécessiter de token Discord réel.
