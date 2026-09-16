import os
import sqlite3
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._open_connections = []
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self._open_connections.append(conn)
        return conn

    def close(self):
        for conn in list(self._open_connections):
            try:
                conn.close()
            except Exception:
                pass
            finally:
                if conn in self._open_connections:
                    self._open_connections.remove(conn)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def init_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Tabela de Usuarios (Controle de Acesso RBAC)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'editor', 'viewer')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Tabela Estruturada de Canais e Conteudos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

            # Tabela de Integracoes Externas e Webhooks
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

            # Provisionamento obrigatorio de usuario root caso a base esteja vazia
            cursor.execute("SELECT COUNT(*) FROM users;")
            if cursor.fetchone()[0] == 0:
                default_hash = generate_password_hash("admin123")
                cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?);",
                               ("admin", default_hash, "admin"))
            conn.commit()

    def upsert_channel(self, ch: Dict[str, Any]):
        record = {
            "url": ch.get("url", ""),
            "name": ch.get("name", "Canal Desconhecido"),
            "metadata": ch.get("metadata", ""),
            "tvg_id": ch.get("tvg_id", ""),
            "logo": ch.get("logo", ""),
            "group_title": ch.get("group_title", ""),
            "country": ch.get("country", "Outros"),
            "state": ch.get("state", "Nacional/Geral"),
            "city": ch.get("city", "Geral"),
            "category": ch.get("category", "tv"),
            "auto_remove_if_offline": int(ch.get("auto_remove_if_offline", 1))
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO channels (url, name, metadata, tvg_id, logo, group_title, country, state, city, category, auto_remove_if_offline)
                VALUES (:url, :name, :metadata, :tvg_id, :logo, :group_title, :country, :state, :city, :category, :auto_remove_if_offline)
                ON CONFLICT(url) DO UPDATE SET
                    name=excluded.name,
                    metadata=excluded.metadata,
                    tvg_id=excluded.tvg_id,
                    logo=excluded.logo,
                    group_title=excluded.group_title,
                    country=excluded.country,
                    state=excluded.state,
                    city=excluded.city,
                    category=excluded.category,
                    auto_remove_if_offline=excluded.auto_remove_if_offline;
            """, record)
            conn.commit()

    def update_channel_status(self, url: str, status: str, latency: float, http_status: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE channels 
                SET status = ?, latency_ms = ?, http_status = ?, last_checked = CURRENT_TIMESTAMP
                WHERE url = ?;
            """, (status, latency, http_status, url))
            conn.commit()

    def delete_purged_channels(self):
        """Remove canais offline cuja flag auto_remove_if_offline esteja ativa."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channels WHERE status = 'offline' AND auto_remove_if_offline = 1;")
            conn.commit()

    def list_channels(self, country: Optional[str] = None, category: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None, sort: str = "id", direction: str = "asc") -> List[Dict[str, Any]]:
        query = "SELECT * FROM channels WHERE 1=1"
        params = []
        if country and country != "todos":
            query += " AND country = ?"
            params.append(country)
        if category and category != "todos":
            query += " AND category = ?"
            params.append(category)
        if status and status != "todos":
            query += " AND status = ?"
            params.append(status)

        if search:
            term = f"%{search.strip()}%"
            query += " AND (name LIKE ? OR url LIKE ? OR tvg_id LIKE ? OR group_title LIKE ? OR country LIKE ? OR state LIKE ? OR city LIKE ?)"
            params.extend([term] * 7)

        sort_columns = {"id", "name", "country", "state", "city", "category", "status", "group_title", "tvg_id", "latency_ms", "last_checked"}
        safe_sort = sort if sort in sort_columns else "id"
        safe_direction = "DESC" if direction.lower() == "desc" else "ASC"

        query += f" ORDER BY {safe_sort} {safe_direction};"
        with self.get_connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def channel_filter_options(self) -> Dict[str, List[str]]:
        with self.get_connection() as conn:
            result = {}
            for field in ("country", "state", "city", "category", "status"):
                rows = conn.execute(
                    f"SELECT DISTINCT {field} FROM channels WHERE {field} IS NOT NULL AND TRIM({field}) != '' ORDER BY {field} COLLATE NOCASE"
                ).fetchall()
                result[field] = [str(row[0]) for row in rows]
            return result

    def update_channel(self, channel_id: int, values: Dict[str, Any]) -> bool:
        allowed = {"url", "name", "tvg_id", "logo", "group_title", "country", "state", "city", "category", "status", "auto_remove_if_offline", "metadata"}
        changes = {key: value for key, value in values.items() if key in allowed}
        if not changes:
            return False
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self.get_connection() as conn:
            cursor = conn.execute(f"UPDATE channels SET {assignments} WHERE id = ?", [*changes.values(), channel_id])
            conn.commit()
            return cursor.rowcount > 0

    def list_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT id, username, role, created_at FROM users ORDER BY id"
            ).fetchall()]

    def create_user(self, username: str, password: str, role: str) -> bool:
        if role not in {"admin", "editor", "viewer"} or not username or not password:
            return False
        with self.get_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username.strip(), generate_password_hash(password), role),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def update_user(self, user_id: int, values: Dict[str, Any]) -> bool:
        changes = {}
        if values.get("username"):
            changes["username"] = str(values["username"]).strip()
        if values.get("role") in {"admin", "editor", "viewer"}:
            changes["role"] = values["role"]
        if values.get("password"):
            changes["password_hash"] = generate_password_hash(values["password"])
        if not changes:
            return False
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self.get_connection() as conn:
            cursor = conn.execute(f"UPDATE users SET {assignments} WHERE id = ?", [*changes.values(), user_id])
            conn.commit()
            return cursor.rowcount > 0

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT id, username, role, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def add_process_event(self, message: str, level: str = "info", run_id: Optional[int] = None):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO process_events (level, message, run_id) VALUES (?, ?, ?)",
                (level, message, run_id)
            )
            conn.commit()

    def list_process_events(self, limit: int = 250) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, level, message, run_id FROM process_events ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 5000)),)
            ).fetchall()
            return [dict(row) for row in rows]

    def start_process_run(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("INSERT INTO process_runs (status) VALUES ('Executando...')")
            conn.commit()
            return cursor.lastrowid

    def finish_process_run(self, run_id: int, status: str, result: Dict[str, Any], message: str):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE process_runs
                SET finished_at = CURRENT_TIMESTAMP, status = ?, total_canais = ?,
                    canais_online = ?, canais_offline = ?, manifestos = ?, last_message = ?
                WHERE id = ?
            """, (status, result.get("total", 0), result.get("online", 0),
                  result.get("offline", 0), len(result.get("partitions", [])), message, run_id))
            conn.commit()

    def list_process_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM process_runs ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 500)),)
            ).fetchall()
            return [dict(row) for row in rows]