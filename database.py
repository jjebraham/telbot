# database.py
import sqlite3
from contextlib import closing
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        # users table (matches what your handlers expect)
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            phone_number TEXT UNIQUE,
            national_id TEXT,
            dob TEXT,
            bank_card_number TEXT,
            accepted_terms INTEGER,
            front_id TEXT,
            back_id TEXT,
            kyc_status TEXT DEFAULT 'Pending',
            reference_code TEXT,
            kyc_notified INTEGER DEFAULT 0,
            created_date TEXT DEFAULT (datetime('now','localtime'))
        )
        """)
        # optional extra cards table, if you use it elsewhere
        c.execute("""
        CREATE TABLE IF NOT EXISTS bank_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_number TEXT,
            UNIQUE(user_id, card_number),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # ✅ add a fast lookup for phone (and keep it unique)
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)")

        conn.commit()

# already existing helpers you had:
def upsert_user(user_id, **fields):
    """Insert if missing, else update."""
    cols = []
    vals = []
    for k, v in fields.items():
        cols.append(k)
        vals.append(v)
    if not cols:
        return
    placeholders = ", ".join(f"{k}=?" for k in cols)
    with get_db_connection() as conn:
        c = conn.cursor()
        # ensure row exists
        c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        c.execute(f"UPDATE users SET {placeholders} WHERE id=?", (*vals, user_id))
        conn.commit()

def get_user(user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None

def set_user_docs(user_id, front_id=None, back_id=None):
    updates = {}
    if front_id is not None:
        updates["front_id"] = front_id
    if back_id is not None:
        updates["back_id"] = back_id
    if updates:
        upsert_user(user_id, **updates)

# 🔥 NEW: what your menu/login flow is importing
def get_user_by_phone(phone: str):
    """Return user row by phone number (e.g. '+98912…')."""
    with get_db_connection() as conn:
        c = conn.cursor()
        row = c.execute("SELECT * FROM users WHERE phone_number=?", (phone,)).fetchone()
        return dict(row) if row else None

