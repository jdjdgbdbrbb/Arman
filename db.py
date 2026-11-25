import sqlite3
from config import DB_PATH

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '',
            balance REAL NOT NULL DEFAULT 0, joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            vip_until TEXT
        );
        CREATE TABLE IF NOT EXISTS videos(
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            url TEXT NOT NULL, reward REAL NOT NULL, min_seconds INTEGER NOT NULL DEFAULT 30,
            active INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS video_claims(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL, claimed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, video_id)
        );
        CREATE TABLE IF NOT EXISTS group_claims(
            user_id INTEGER PRIMARY KEY, claimed_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS withdrawals(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount REAL NOT NULL, method TEXT NOT NULL, account TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS watch_sessions(
            user_id INTEGER NOT NULL, video_id INTEGER NOT NULL,
            started_at REAL NOT NULL, PRIMARY KEY(user_id, video_id)
        );
        """)
