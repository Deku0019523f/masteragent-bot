# plan.md — Structure détaillée du projet Master Agent

```
masteragent/
│
├── bot.py
│     Point d'entrée. Classe MasterAgentBot(commands.Bot) :
│       - setup_hook() : connecte la DB, charge les 9 extensions (cogs),
│         ré-enregistre les persistent views (RulesAcceptView), sync le tree.
│       - on_ready() : log + présence "Watching la communauté Master Agent 🚀"
│       - on_disconnect() / close() : ferme proprement la connexion DB.
│       - Gestionnaire d'erreurs global @bot.tree.error (fallback si le cog
│         n'a pas son propre cog_app_command_error).
│
├── config.py
│     - Settings : lit .env (token, préfixe, log level, chemin DB, flags par défaut)
│     - SERVER_BLUEPRINT : dict décrivant tous les rôles/catégories/salons que
│       /setup doit créer. Source unique de vérité pour la structure serveur.
│
├── requirements.txt / requirements-dev.txt
├── .env.example
├── .gitignore
├── masteragent.service       (unit systemd pour déploiement VPS)
│
├── cogs/
│   ├── setup.py
│   │     /setup (idempotent, owner/admin only) : crée rôles → catégories → salons
│   │     → sauvegarde config → poste panneau règlement + panneau tickets.
│   │     /reset config (efface juste les IDs enregistrés en base)
│   │     /reset masteragent (destructif, double confirmation, groupe "reset")
│   │
│   ├── welcome.py
│   │     on_member_join : attribue "Nouveau membre", poste message de bienvenue.
│   │     on_member_remove : log dans #logs.
│   │
│   ├── moderation.py
│   │     /warn /warnings /clear /timeout /untimeout /kick /ban /unban /lock /unlock
│   │     Toutes les commandes sensibles passent par _hierarchy_check() avant
│   │     d'agir. Auto-timeout si seuil de warnings atteint (configurable).
│   │
│   ├── administration.py
│   │     Groupe "role" : add/remove/info/list — vérifie can_assign_role().
│   │     /config : affiche/modifie les flags (welcome/tickets/projects/voice enabled).
│   │
│   ├── tickets.py
│   │     Cog "coquille" : au cog_load(), enregistre les 3 persistent views du
│   │     système de tickets (panel, category select, controls) pour qu'elles
│   │     survivent à un redémarrage.
│   │
│   ├── projects.py
│   │     /agent : ouvre le modal ProjectModal, publie l'embed dans
│   │     🚀・mes-agents (résolu dynamiquement via server_resources).
│   │
│   ├── member.py
│   │     /profile (soi-même → modal de configuration ; @membre → affichage)
│   │     /userinfo /serverinfo /members
│   │
│   ├── staff.py
│   │     Groupe "staff" : list/add/remove/promote/demote — roster distinct
│   │     des rôles Discord bruts, avec historique dans staff_actions.
│   │
│   └── utility.py
│         /ping /about /rules /stats /help (adapté au rôle de l'appelant)
│
├── database/
│   ├── models.py
│   │     DDL pur : guilds, server_resources, members, profiles, warnings,
│   │     moderation_logs, tickets, projects, staff_actions, staff_members
│   │     + index sur les colonnes de recherche fréquentes.
│   │
│   └── database.py
│         Classe Database : une connexion aiosqlite partagée + asyncio.Lock
│         (évite les "database is locked"), PRAGMA WAL + foreign_keys.
│         Méthodes haut niveau par domaine : guilds/, resources/, members/,
│         warnings/, tickets/, projects/, profiles/, staff/.
│
├── views/
│   ├── welcome_view.py
│   │     RulesAcceptView (persistent, custom_id fixe) : bouton "J'accepte
│   │     le règlement" → bascule Nouveau membre → Membre vérifié.
│   │
│   ├── ticket_view.py
│   │     TicketPanelView → TicketCategoryView/TicketCategorySelect (menu
│   │     déroulant 5 catégories) → crée le salon privé → TicketControlView
│   │     (prendre en charge / fermer / supprimer). Tout est persistent.
│   │
│   ├── project_view.py
│   │     ProjectModal : formulaire "Présenter mon agent" (nom, cas d'usage,
│   │     intégrations, liens doc/démo, ouverture aux retours).
│   │
│   └── confirmation_view.py
│         ConfirmationView générique (boutons Confirmer/Annuler), utilisée
│         par /reset.
│
├── utils/
│   ├── permissions.py   → is_hierarchy_safe(), bot_can_act_on(), can_assign_role()
│   ├── embeds.py        → builders centralisés (success/error/warning/info/
│   │                       moderation_log/project_embed/profile_embed)
│   ├── checks.py        → is_owner_or_admin(), has_staff_role(), guild_configured()
│   ├── logger.py        → logging fichier rotatif (5MB x5) + console
│   └── helpers.py       → parse_duration("10m"→600s), format_duration(), etc.
│
├── tests/
│   ├── test_database.py     (schéma, config, warnings, idempotence resources,
│   │                          profils, tickets, staff — DB temporaire, sans token)
│   ├── test_permissions.py  (hiérarchie de rôles avec objets factices)
│   └── test_helpers.py      (parse/format de durée)
│
└── logs/
      afrocodeurs.log → masteragent.log (rotatif, généré au runtime, absent du repo)
```

## Rôles créés par /setup (ordre hiérarchique, du plus haut au plus bas)

1. 👑 Fondateur (admin)
2. 🛡️ Administrateur (admin)
3. 🔨 Modérateur
4. 🤝 Responsable Communauté
5. 🎓 Expert Automatisation
6. 🤖 Créateur d'agents
7. 💼 Client Pro
8. ⭐ Membre vérifié
9. 🌱 Nouveau membre
10. ⚙️ Bot

## Catégories / salons créés par /setup

| Catégorie | Salons |
|---|---|
| 📢 INFORMATIONS | annonces, bienvenue, reglement, informations, masteragent (lecture seule) |
| 💬 COMMUNAUTÉ | general, presentations, entraide, idees-suggestions, cas-usage |
| 🤖 AGENTS IA | mes-agents, automatisations-avancees, experimentations, tutoriels, outils-integrations, whatsapp-business |
| 📚 RESSOURCES | documentation (lecture seule), faq, changelog (lecture seule), bonnes-pratiques |
| 🎫 SUPPORT | support, bugs-signalements |
| 🔊 VOCAL | Discussion, Réunion de groupe, Réunion privée, Pause |
| 🛡️ STAFF | logs, moderation, tickets-staff, staff (accès restreint) |

## Flux clés

**Accueil** : arrivée → rôle Nouveau membre → message #bienvenue → clic "J'accepte
le règlement" dans #reglement → rôle Membre vérifié.

**Ticket** : clic panneau #support → choix catégorie (menu) → salon privé créé
sous 🛡️ STAFF avec permissions restreintes (opener + staff + bot) → claim/close/delete.

**Présentation d'agent** : `/agent` → modal → embed publié dans #mes-agents,
enregistré en base (table `projects`) avec l'auteur, les intégrations et les liens.
