import os
import sqlite3
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Abre uma conexão curta; o chamador deve usar ``with``.

        Conexões SQLite usadas com ``with`` são fechadas pelo próprio contexto.
        A versão anterior mantinha toda conexão em uma lista permanente, fazendo
        a lista crescer a cada requisição e retendo milhares de objetos fechados.
        Isso era uma fonte real de crescimento contínuo do processo Python.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def close(self):
        """Compatibilidade legada: não há conexões persistentes para fechar."""
        return None

    def __del__(self):
        return None

    def init_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'editor', 'viewer')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_number INTEGER,
                    url TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    metadata TEXT,
                    tvg_id TEXT,
                    logo TEXT DEFAULT '',
                    group_title TEXT,
                    country TEXT DEFAULT 'Outros',
                    state TEXT DEFAULT 'Nacional/Geral',
                    city TEXT DEFAULT 'Geral',
                    category TEXT NOT NULL CHECK(category IN ('tv', 'vod', 'series', 'radio', 'outros')),
                    status TEXT NOT NULL DEFAULT 'desconhecido' CHECK(status IN ('online', 'offline', 'desconhecido')),
                    latency_ms REAL DEFAULT 0.0,
                    http_status INTEGER DEFAULT 0,
                    auto_remove_if_offline INTEGER DEFAULT 1,
                    last_checked DATETIME
                );
            """)
            try:
                cursor.execute("ALTER TABLE channels ADD COLUMN logo TEXT DEFAULT '';" )
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE channels ADD COLUMN channel_number INTEGER;")
            except sqlite3.OperationalError:
                pass
            cursor.execute("UPDATE channels SET channel_number = id WHERE channel_number IS NULL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL DEFAULT 'editor',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS process_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL DEFAULT 'info',
                    message TEXT NOT NULL,
                    run_id INTEGER
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS process_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    finished_at DATETIME,
                    status TEXT NOT NULL,
                    total_canais INTEGER DEFAULT 0,
                    canais_online INTEGER DEFAULT 0,
                    canais_offline INTEGER DEFAULT 0,
                    manifestos INTEGER DEFAULT 0,
                    last_message TEXT
                );
            """)
            cursor.execute("SELECT COUNT(*) FROM users;")
            if cursor.fetchone()[0] == 0:
                default_hash = generate_password_hash("admin123")
                cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?);", ("admin", default_hash, "admin"))
            conn.commit()

    def upsert_channel(self, ch: Dict[str, Any]):
        record = {
            "url": ch.get("url", ""), "channel_number": ch.get("channel_number"), "name": ch.get("name", "Canal Desconhecido"),
            "metadata": ch.get("metadata", ""), "tvg_id": ch.get("tvg_id", ""), "logo": ch.get("logo", ""), "group_title": ch.get("group_title", ""),
            "country": ch.get("country", "Outros"), "state": ch.get("state", "Nacional/Geral"), "city": ch.get("city", "Geral"),
            "category": ch.get("category", "tv"), "auto_remove_if_offline": int(ch.get("auto_remove_if_offline", 1))
        }
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO channels (url, channel_number, name, metadata, tvg_id, logo, group_title, country, state, city, category, auto_remove_if_offline)
                VALUES (:url, :channel_number, :name, :metadata, :tvg_id, :logo, :group_title, :country, :state, :city, :category, :auto_remove_if_offline)
                ON CONFLICT(url) DO UPDATE SET
                    channel_number=COALESCE(channels.channel_number, excluded.channel_number), name=excluded.name,
                    metadata=excluded.metadata, tvg_id=excluded.tvg_id, logo=excluded.logo, group_title=excluded.group_title,
                    country=excluded.country, state=excluded.state, city=excluded.city, category=excluded.category,
                    auto_remove_if_offline=excluded.auto_remove_if_offline;
            """, record)
            conn.commit()

    def create_channel(self, ch: Dict[str, Any]) -> Optional[int]:
        """Cria um canal manualmente sem depender da importação de uma M3U."""
        required = str(ch.get("url", "")).strip()
        name = str(ch.get("name", "")).strip()
        category = str(ch.get("category", "tv")).strip()
        if not required or not name or category not in {"tv", "vod", "series", "radio", "outros"}:
            return None
        with self.get_connection() as conn:
            try:
                cur = conn.execute("""
                    INSERT INTO channels (channel_number, url, name, metadata, tvg_id, logo, group_title, country, state, city, category, status, auto_remove_if_offline)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'desconhecido', ?)
                """, (
                    ch.get("channel_number"), required, name, str(ch.get("metadata", "")), str(ch.get("tvg_id", "")),
                    str(ch.get("logo", "")), str(ch.get("group_title", "")), str(ch.get("country", "Outros")),
                    str(ch.get("state", "Nacional/Geral")), str(ch.get("city", "Geral")), category,
                    1 if ch.get("auto_remove_if_offline", True) else 0,
                ))
                conn.commit()
                return int(cur.lastrowid)
            except sqlite3.IntegrityError:
                return None

    def delete_channel(self, channel_id: int) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
            conn.commit()
            return cur.rowcount > 0

    def update_channel_status(self, url: str, status: str, latency: float, http_status: int):
        with self.get_connection() as conn:
            conn.execute("UPDATE channels SET status = ?, latency_ms = ?, http_status = ?, last_checked = CURRENT_TIMESTAMP WHERE url = ?;", (status, latency, http_status, url))
            conn.commit()

    def delete_purged_channels(self):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM channels WHERE status = 'offline' AND auto_remove_if_offline = 1;")
            conn.commit()

    def list_channels(self, country: Optional[str] = None, category: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None, sort: str = "id", direction: str = "asc") -> List[Dict[str, Any]]:
        query = "SELECT * FROM channels WHERE 1=1"
        params = []
        if country and country != "todos": query += " AND country = ?"; params.append(country)
        if category and category != "todos": query += " AND category = ?"; params.append(category)
        if status and status != "todos": query += " AND status = ?"; params.append(status)
        if search: query += " AND (name LIKE ? OR url LIKE ? OR group_title LIKE ? OR tvg_id LIKE ? OR city LIKE ?)"; term = f"%{search}%"; params.extend([term] * 5)
        allowed_sort = {"id", "channel_number", "name", "country", "state", "city", "group_title", "tvg_id", "latency_ms", "status"}
        query += f" ORDER BY {sort if sort in allowed_sort else 'id'} {'DESC' if direction == 'desc' else 'ASC'}"
        with self.get_connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def channel_filter_options(self):
        with self.get_connection() as conn:
            return {
                "country": [row[0] for row in conn.execute("SELECT DISTINCT country FROM channels WHERE country IS NOT NULL AND country != '' ORDER BY country").fetchall()],
                "state": [row[0] for row in conn.execute("SELECT DISTINCT state FROM channels WHERE state IS NOT NULL AND state != '' ORDER BY state").fetchall()],
                "city": [row[0] for row in conn.execute("SELECT DISTINCT city FROM channels WHERE city IS NOT NULL AND city != '' ORDER BY city").fetchall()],
                "category": [row[0] for row in conn.execute("SELECT DISTINCT category FROM channels ORDER BY category").fetchall()],
                "status": [row[0] for row in conn.execute("SELECT DISTINCT status FROM channels ORDER BY status").fetchall()],
            }

    def add_process_event(self, message: str, level: str = "info", run_id: Optional[int] = None):
        with self.get_connection() as conn:
            conn.execute("INSERT INTO process_events (level, message, run_id) VALUES (?, ?, ?)", (level, message, run_id))
            conn.commit()

    def list_process_events(self, limit: int = 250):
        with self.get_connection() as conn:
            return [dict(row) for row in conn.execute("SELECT timestamp, level, message, run_id FROM process_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 1000)),)).fetchall()]

    def list_process_runs(self, limit: int = 20):
        with self.get_connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM process_runs ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),)).fetchall()]
