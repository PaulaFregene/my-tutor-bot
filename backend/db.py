import logging
import sqlite3
import time

# Set up logging
logging.basicConfig(level=logging.ERROR)

# Improved SQLite connection with better concurrency handling
conn = sqlite3.connect(
    "conversations.db",
    check_same_thread=False,
    timeout=10.0,  # Wait up to 10 seconds for write locks
    isolation_level="DEFERRED",  # Better concurrent read performance
)
# Enable WAL mode for better concurrent access
conn.execute("PRAGMA journal_mode=WAL")
c = conn.cursor()

# 1. Create table
try:
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_user_id TEXT,
            role TEXT,
            content TEXT,
            mode TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
    # 2. PERFORMANCE FIX: Create an Index on anon_user_id
    # This makes lookups O(1) instead of O(N) - instant access even with millions of rows.
    c.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(anon_user_id)")
    conn.commit()
except sqlite3.Error as e:
    conn.rollback()
    logging.error("Error setting up DB: %s", e)

# ... (Check for mode column code stays the same) ...


def save_message(anon_user_id, role, content, mode):
    # ... (Keep existing logic) ...
    try:
        c.execute(
            "INSERT INTO conversations (anon_user_id, role, content, mode) VALUES (?, ?, ?, ?)",
            (anon_user_id, role, content, mode),
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logging.error("Error saving: %s", e)


def get_history(anon_user_id, limit=10):
    """
    Fetch only the most recent 'limit' messages.
    """
    try:
        # 3. PERFORMANCE FIX: Use LIMIT in SQL
        # We sort DESC (newest first) to get the last 10, then Python reverses it back to normal order.
        c.execute(
            """
            SELECT role, content, mode 
            FROM conversations 
            WHERE anon_user_id = ? 
            ORDER BY id DESC 
            LIMIT ?
            """,
            (anon_user_id, limit),
        )
        rows = c.fetchall()

        # Reverse them back so they are in chronological order (Oldest -> Newest)
        history = [
            {"role": r[0], "content": r[1], "mode": r[2]} for r in reversed(rows)
        ]
        return history
    except sqlite3.Error as e:
        logging.error("Error getting history: %s", e)
        return []
