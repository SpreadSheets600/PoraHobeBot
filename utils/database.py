import sqlite3


def initialize_database(db_name="notes.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            file_url TEXT,
            channel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            tags TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT,
            channel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            type TEXT  -- youtube, drive, etc.
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reactions (
            note_id INTEGER,
            reaction TEXT,
            count INTEGER DEFAULT 1,
            FOREIGN KEY(note_id) REFERENCES notes(id)
        )
        """
    )

    conn.commit()
    return conn
