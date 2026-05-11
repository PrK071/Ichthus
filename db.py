import sqlite3

DB_NAME = "iloveso2.db"

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")

    cur.execute("CREATE TABLE IF NOT EXISTS fingerprints (hash TEXT, song_id INTEGER, offset INTEGER)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_hash ON fingerprints (hash)")
    conn.commit()
    return conn
