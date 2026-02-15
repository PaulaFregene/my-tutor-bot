# SQLite conversation DB

import sqlite3
import time
import logging

# Set up logging
logging.basicConfig(level=logging.ERROR)

conn = sqlite3.connect("conversations.db", check_same_thread=False)
c = conn.cursor()

# Create table if not exists
try:
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_user_id TEXT,
            role TEXT,
            content TEXT,
            mode TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
except sqlite3.Error as e:
    logging.error("Error creating table: %s", e)

# Check if mode column exists, if not, add it
try:
    c.execute("PRAGMA table_info(conversations)")
    columns = [row[1] for row in c.fetchall()]
    if "mode" not in columns:
        c.execute("ALTER TABLE conversations ADD COLUMN mode TEXT")
        conn.commit()
        logging.info("Added mode column to conversations table")
except sqlite3.Error as e:
    logging.error("Error checking/adding mode column: %s", e)


#
# save_message
#
# Saves the message and insert it into the conversation database
def save_message(anon_user_id, role, content, mode):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            c.execute(
                "INSERT INTO conversations (anon_user_id, role, content, mode) VALUES (?, ?, ?, ?)",
                (anon_user_id, role, content, mode),
            )
            conn.commit()
            return
        except sqlite3.Error as e:
            logging.error("Error saving message (attempt %d): %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(2**attempt)  # Exponential backoff
            else:
                raise e


def get_history(anon_user_id):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            c.execute(
                "SELECT role, content, mode FROM conversations WHERE anon_user_id = ? ORDER BY id",
                (anon_user_id,),
            )
            return [
                {"role": row[0], "content": row[1], "mode": row[2]}
                for row in c.fetchall()
            ]
        except sqlite3.Error as e:
            logging.error("Error getting history (attempt %d): %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(2**attempt)  # Exponential backoff
            else:
                raise e
