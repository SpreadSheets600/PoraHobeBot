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


def update_note(conn, note_id, title=None, content=None, file_url=None, tags=None):
    cursor = conn.cursor()
    fields = []
    params = []

    if title is not None:
        fields.append("title = ?")
        params.append(title)

    if content is not None:
        fields.append("content = ?")
        params.append(content)

    if file_url is not None:
        fields.append("file_url = ?")
        params.append(file_url)

    if tags is not None:
        fields.append("tags = ?")
        params.append(tags)

    if not fields:
        raise ValueError("No fields to update.")

    params.append(note_id)

    sql = f"UPDATE notes SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(sql, tuple(params))
    conn.commit()

    return cursor.rowcount


def get_note_by_id(conn, note_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, content, file_url, tags, user_id FROM notes WHERE id = ?",
        (note_id,),
    )
    row = cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "file_url": row[3],
            "tags": row[4],
            "user_id": row[5],
        }
    return None


def update_table(conn):
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE notes ADD COLUMN thumbnail_url TEXT;")
    conn.commit()
