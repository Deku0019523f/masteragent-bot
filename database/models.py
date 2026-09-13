"""
database/models.py
SQL schema definitions for Master Agent. Pure DDL — no logic here.
"""

SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS guilds (
        guild_id INTEGER PRIMARY KEY,
        setup_status TEXT NOT NULL DEFAULT 'not_started',
        welcome_channel INTEGER,
        rules_channel INTEGER,
        logs_channel INTEGER,
        support_channel INTEGER,
        moderation_channel INTEGER,
        announcements_channel INTEGER,
        staff_category INTEGER,
        member_role INTEGER,
        new_member_role INTEGER,
        admin_role INTEGER,
        moderator_role INTEGER,
        founder_role INTEGER,
        bot_role INTEGER,
        welcome_enabled INTEGER NOT NULL DEFAULT 1,
        tickets_enabled INTEGER NOT NULL DEFAULT 1,
        projects_enabled INTEGER NOT NULL DEFAULT 1,
        voice_enabled INTEGER NOT NULL DEFAULT 0,
        warn_timeout_threshold INTEGER NOT NULL DEFAULT 3,
        warn_major_threshold INTEGER NOT NULL DEFAULT 5,
        rules_text TEXT,
        welcome_message TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS server_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        resource_type TEXT NOT NULL,      -- 'role' | 'category' | 'channel'
        resource_key TEXT NOT NULL,       -- logical name from blueprint (e.g. '💬・general')
        discord_id INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(guild_id, resource_type, resource_key),
        FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL DEFAULT (datetime('now')),
        verified INTEGER NOT NULL DEFAULT 0,
        UNIQUE(guild_id, user_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        display_name TEXT,
        domain TEXT,
        skills TEXT,
        technologies TEXT,
        bio TEXT,
        github TEXT,
        portfolio TEXT,
        socials TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(guild_id, user_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        moderator_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS moderation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        moderator_id INTEGER NOT NULL,
        action TEXT NOT NULL,           -- warn | timeout | untimeout | kick | ban | unban | clear | lock | unlock
        reason TEXT,
        duration_seconds INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        opener_id INTEGER NOT NULL,
        category TEXT NOT NULL,          -- support | collaboration | signalement | partenariat | autre
        status TEXT NOT NULL DEFAULT 'open',  -- open | claimed | closed
        claimed_by INTEGER,
        closed_by INTEGER,
        close_reason TEXT,
        ticket_number INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        closed_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        technologies TEXT,
        github_link TEXT,
        demo_link TEXT,
        seeking_collaborators INTEGER NOT NULL DEFAULT 0,
        message_id INTEGER,
        channel_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        staff_user_id INTEGER NOT NULL,
        actor_id INTEGER NOT NULL,
        action TEXT NOT NULL,     -- added | removed | promoted | demoted
        details TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role_label TEXT NOT NULL,
        joined_staff_at TEXT NOT NULL DEFAULT (datetime('now')),
        actions_count INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(guild_id, user_id)
    );
    """,
]

INDEX_STATEMENTS: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_warnings_guild_user ON warnings(guild_id, user_id);",
    "CREATE INDEX IF NOT EXISTS idx_modlogs_guild_user ON moderation_logs(guild_id, user_id);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_guild_status ON tickets(guild_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_projects_guild ON projects(guild_id);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_guild_user ON profiles(guild_id, user_id);",
    "CREATE INDEX IF NOT EXISTS idx_resources_guild ON server_resources(guild_id, resource_type);",
    "CREATE INDEX IF NOT EXISTS idx_staff_guild ON staff_members(guild_id, active);",
]
