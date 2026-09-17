import os
import sqlite3
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash


class _ManagedConnection(sqlite3.Connection):
    """SQLite connection that also closes when leaving a ``with`` block.

    ``sqlite3.Connection.__exit__`` commits/rolls back the transaction, but it
    does not close the connection. On Windows this can keep ``app.db`` locked
    until garbage collection, causing temporary-directory test failures and
    unnecessary RSS growth in long-running processes.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        # Callers use this connection through ``with``. The managed connection
        # closes deterministically instead of remaining alive until GC.
        conn = sqlite3.connect(self.db_path, factory=_ManagedConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def close(self):
        # Connections are owned by their ``with`` blocks. Kept for compatibility
        # with older callers that explicitly call Database.close().
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
            try: cursor.execute("ALTER TABLE channels ADD COLUMN logo TEXT DEFAULT '';")
            except sqlite3.OperationalError: pass
            try: cursor.execute("ALTER TABLE channels ADD COLUMN channel_number INTEGER;")
            except sqlite3.OperationalError: pass
            cursor.execute("UPDATE channels SET channel_number = id WHERE channel_number IS NULL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL, role TEXT NOT NULL DEFAULT 'editor',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS process_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL DEFAULT 'info', message TEXT NOT NULL, run_id INTEGER
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS process_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    finished_at DATETIME, status TEXT NOT NULL, total_canais INTEGER DEFAULT 0,
                    canais_online INTEGER DEFAULT 0, canais_offline INTEGER DEFAULT 0,
                    manifestos INTEGER DEFAULT 0, last_message TEXT
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
                ON CONFLICT(url) DO UPDATE SET channel_number=COALESCE(channels.channel_number, excluded.channel_number),
                name=excluded.name, metadata=excluded.metadata, tvg_id=excluded.tvg_id, logo=excluded.logo,
                group_title=excluded.group_title, country=excluded.country, state=excluded.state, city=excluded.city,
                category=excluded.category, auto_remove_if_offline=excluded.auto_remove_if_offline;
            """, record)
            conn.commit()

    def update_channel_status(self, url: str, status: str, latency: float, http_status: int):
        with self.get_connection() as conn:
            conn.execute("UPDATE channels SET status = ?, latency_ms = ?, http_status = ?, last_checked = CURRENT_TIMESTAMP WHERE url = ?;", (status, latency, http_status, url)); conn.commit()

    def delete_purged_channels(self):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM channels WHERE status = 'offline' AND auto_remove_if_offline = 1;"); conn.commit()

    def list_channels(self, country: Optional[str] = None, category: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None, sort: str = "id", direction: str = "asc") -> List[Dict[str, Any]]:
        query = "SELECT * FROM channels WHERE 1=1"; params = []
        if country and country != "todos": query += " AND country = ?"; params.append(country)
        if category and category != "todos": query += " AND category = ?"; params.append(category)
        if status and status != "todos": query += " AND status = ?"; params.append(status)
        if search:
            term = f"%{search.strip()}%"; query += " AND (name LIKE ? OR url LIKE ? OR tvg_id LIKE ? OR group_title LIKE ? OR country LIKE ? OR state LIKE ? OR city LIKE ?)"; params.extend([term] * 7)
        sort_columns = {"id", "channel_number", "name", "country", "state", "city", "category", "status", "group_title", "tvg_id", "latency_ms", "last_checked"}
        query += f" ORDER BY {sort if sort in sort_columns else 'id'} {'DESC' if direction.lower() == 'desc' else 'ASC'};"
        with self.get_connection() as conn: return [dict(row) for row in conn.execute(query, params).fetchall()]

    def channel_filter_options(self) -> Dict[str, List[str]]:
        with self.get_connection() as conn:
            return {field: [str(row[0]) for row in conn.execute(f"SELECT DISTINCT {field} FROM channels WHERE {field} IS NOT NULL AND TRIM({field}) != '' ORDER BY {field} COLLATE NOCASE").fetchall()] for field in ("country", "state", "city", "category", "status")}

    def update_channel(self, channel_id: int, values: Dict[str, Any]) -> bool:
        allowed = {"url", "channel_number", "name", "tvg_id", "logo", "group_title", "country", "state", "city", "category", "status", "auto_remove_if_offline", "metadata"}
        changes = {key: value for key, value in values.items() if key in allowed}
        if "channel_number" in changes:
            raw = changes["channel_number"]
            if raw in ("", None): changes["channel_number"] = None
            else:
                try: changes["channel_number"] = max(0, int(raw))
                except (TypeError, ValueError): return False
        if not changes: return False
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self.get_connection() as conn:
            cursor = conn.execute(f"UPDATE channels SET {assignments} WHERE id = ?", [*changes.values(), channel_id]); conn.commit(); return cursor.rowcount > 0

    def delete_channel(self, channel_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,)); conn.commit(); return cursor.rowcount > 0

    def create_channel(self, ch: Dict[str, Any]) -> Optional[int]:
        url = str(ch.get("url", "")).strip(); name = str(ch.get("name", "")).strip(); category = str(ch.get("category", "tv")).strip()
        if not url or not name or category not in {"tv", "vod", "series", "radio", "outros"}: return None
        with self.get_connection() as conn:
            try:
                cur = conn.execute("""INSERT INTO channels (channel_number,url,name,metadata,tvg_id,logo,group_title,country,state,city,category,status,auto_remove_if_offline) VALUES (?,?,?,?,?,?,?,?,?,?,?,'desconhecido',?)""", (ch.get("channel_number"),url,name,str(ch.get("metadata", "")),str(ch.get("tvg_id", "")),str(ch.get("logo", "")),str(ch.get("group_title", "")),str(ch.get("country", "Outros")),str(ch.get("state", "Nacional/Geral")),str(ch.get("city", "Geral")),category,1 if ch.get("auto_remove_if_offline", True) else 0)); conn.commit(); return int(cur.lastrowid)
            except sqlite3.IntegrityError: return None

    def list_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn: return [dict(row) for row in conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id").fetchall()]

    def create_user(self, username: str, password: str, role: str) -> bool:
        if role not in {"admin", "editor", "viewer"} or not username or not password: return False
        with self.get_connection() as conn:
            try: conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username.strip(), generate_password_hash(password), role)); conn.commit(); return True
            except sqlite3.IntegrityError: return False

    def update_user(self, user_id: int, values: Dict[str, Any]) -> bool:
        changes = {}
        if values.get("username"): changes["username"] = str(values["username"]).strip()
        if values.get("role") in {"admin", "editor", "viewer"}: changes["role"] = values["role"]
        if values.get("password"): changes["password_hash"] = generate_password_hash(values["password"])
        if not changes: return False
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self.get_connection() as conn: cursor = conn.execute(f"UPDATE users SET {assignments} WHERE id = ?", [*changes.values(), user_id]); conn.commit(); return cursor.rowcount > 0

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT id, username, role, created_at FROM users WHERE id = ?", (user_id,)).fetchone(); return dict(row) if row else None

    def add_process_event(self, message: str, level: str = "info", run_id: Optional[int] = None):
        with self.get_connection() as conn: conn.execute("INSERT INTO process_events (level, message, run_id) VALUES (?, ?, ?)", (level, message, run_id)); conn.commit()

    def list_process_events(self, limit: int = 250) -> List[Dict[str, Any]]:
        with self.get_connection() as conn: return [dict(row) for row in conn.execute("SELECT id, timestamp, level, message, run_id FROM process_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 5000)),)).fetchall()]

    def start_process_run(self) -> int:
        with self.get_connection() as conn: cursor = conn.execute("INSERT INTO process_runs (status) VALUES ('Executando...')"); conn.commit(); return cursor.lastrowid

    def finish_process_run(self, run_id: int, status: str, result: Dict[str, Any], message: str):
        with self.get_connection() as conn: conn.execute("UPDATE process_runs SET finished_at=CURRENT_TIMESTAMP,status=?,total_canais=?,canais_online=?,canais_offline=?,manifestos=?,last_message=? WHERE id=?", (status,result.get("total",0),result.get("online",0),result.get("offline",0),len(result.get("partitions",[])),message,run_id)); conn.commit()

    def list_process_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn: return [dict(row) for row in conn.execute("SELECT * FROM process_runs ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()]
