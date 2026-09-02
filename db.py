"""SQLite 初始化与通用操作"""
import sqlite3
from config import DB_PATH

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS monitor_links(
            asin TEXT PRIMARY KEY,
            note TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')))""")
        c.execute("""CREATE TABLE IF NOT EXISTS snapshots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT NOT NULL,
            fetched_at TEXT DEFAULT (datetime('now','localtime')),
            title TEXT,
            price REAL,
            buybox_seller TEXT,
            sellers_count INTEGER,
            rating REAL,
            review_count INTEGER,
            raw TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS diffs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT NOT NULL,
            fetched_at TEXT DEFAULT (datetime('now','localtime')),
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            severity TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asin TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            message TEXT,
            severity TEXT,
            is_read INTEGER DEFAULT 0)""")

def seed_links(seeds):
    with get_conn() as c:
        for s in seeds:
            c.execute("INSERT OR IGNORE INTO monitor_links(asin, note) VALUES(?, ?)",
                      (s["asin"], s["note"]))