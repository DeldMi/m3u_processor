"""RBAC granular, perfis de usuário e contratos de autorização."""
from __future__ import annotations
import sqlite3
from typing import Any, Dict, Iterable, Optional
from werkzeug.security import generate_password_hash

ACTIONS = ("view", "create", "edit", "delete", "execute", "admin")
RESOURCES = ("dashboard", "channels", "playlists", "epg", "sync", "health", "settings", "users", "logs", "maintenance", "public_files", "system")
ROLE_PERMISSIONS = {
    "viewer": {"dashboard":{"view"},"channels":{"view"},"playlists":{"view"},"epg":{"view"},"health":{"view"}},
    "editor": {"dashboard":{"view"},"channels":{"view","create","edit"},"playlists":{"view","create","edit"},"epg":{"view","create","edit"},"sync":{"view","execute"},"health":{"view"}},
    "admin": {resource:set(ACTIONS) for resource in RESOURCES},
}
PERMISSION_CATALOG = [
    {"resource":"dashboard","label":"Painel geral","description":"Métricas e visão operacional."},{"resource":"channels","label":"Canais","description":"Cadastro, filtros, edição e status."},{"resource":"playlists","label":"Playlists","description":"Listas M3U publicadas."},{"resource":"epg","label":"EPG/XMLTV","description":"Arquivos XMLTV."},{"resource":"sync","label":"Sincronização","description":"Execução do processamento."},{"resource":"health","label":"Monitoramento","description":"Internet, latência e saúde."},{"resource":"settings","label":"Configurações","description":"Configurações e integrações."},{"resource":"users","label":"Usuários","description":"Contas, perfis e permissões."},{"resource":"logs","label":"Logs","description":"Eventos e histórico."},{"resource":"maintenance","label":"Manutenção","description":"Limpeza e diagnóstico."},{"resource":"public_files","label":"Arquivos públicos","description":"M3U/XMLTV publicados."},{"resource":"system","label":"Sistema","description":"Operações administrativas."},
]


def _permissions_table(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS user_permissions (user_id INTEGER NOT NULL, resource TEXT NOT NULL, action TEXT NOT NULL, allowed INTEGER NOT NULL DEFAULT 1, PRIMARY KEY (user_id, resource, action), FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)")


def _add_column(conn: sqlite3.Connection, name: str, definition: str) -> None:
    try: conn.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower(): raise


def ensure_schema(db: Any) -> None:
    with db.get_connection() as conn:
        for name, definition in (("display_name","TEXT DEFAULT ''"),("full_name","TEXT DEFAULT ''"),("email","TEXT DEFAULT ''"),("avatar","TEXT DEFAULT ''"),("phone","TEXT DEFAULT ''"),("description","TEXT DEFAULT ''"),("department","TEXT DEFAULT ''"),("active","INTEGER NOT NULL DEFAULT 1"),("expires_at","DATETIME")): _add_column(conn,name,definition)
        _permissions_table(conn); conn.commit()


def permissions_for_role(role: str) -> Dict[str,set[str]]:
    return {resource:set(actions) for resource,actions in ROLE_PERMISSIONS.get(role,{}).items()}


def _normalise_permissions(values: Any) -> Dict[str,set[str]]:
    result={}
    if not isinstance(values,dict): return result
    for resource,actions in values.items():
        if resource in RESOURCES and isinstance(actions,Iterable) and not isinstance(actions,(str,bytes)): result[resource]={str(a) for a in actions if str(a) in ACTIONS}
    return result


def _store_exact_permissions(conn,user_id:int,values:Any)->None:
    permissions=_normalise_permissions(values);conn.execute("DELETE FROM user_permissions WHERE user_id=?",(user_id,))
    for resource in RESOURCES:
        for action in ACTIONS: conn.execute("INSERT INTO user_permissions(user_id,resource,action,allowed) VALUES(?,?,?,?)",(user_id,resource,action,1 if action in permissions.get(resource,set()) else 0))


def get_user_permissions(db:Any,user_id:int,role:str)->Dict[str,set[str]]:
    permissions=permissions_for_role(role)
    with db.get_connection() as conn: rows=conn.execute("SELECT resource,action,allowed FROM user_permissions WHERE user_id=?",(user_id,)).fetchall()
    for row in rows:
        resource,action=row["resource"],row["action"];permissions.setdefault(resource,set())
        if row["allowed"]: permissions[resource].add(action)
        else: permissions[resource].discard(action)
    return permissions


def has_permission(db:Any,user_id:int,role:str,resource:str,action:str)->bool:
    return action in ACTIONS and resource in RESOURCES and action in get_user_permissions(db,user_id,role).get(resource,set())


def permission_payload(db:Any,user_id:int,role:str)->Dict[str,list[str]]:
    return {r:sorted(a) for r,a in get_user_permissions(db,user_id,role).items() if a}


def public_user(db:Any,user_id:int)->Optional[Dict[str,Any]]:
    with db.get_connection() as conn:
        row=conn.execute("SELECT id,username,role,created_at,display_name,full_name,email,avatar,phone,description,department,active,expires_at FROM users WHERE id=?",(user_id,)).fetchone()
    if not row:return None
    data=dict(row);data["permissions"]=permission_payload(db,user_id,data["role"]);return data


def list_public_users(db:Any)->list[Dict[str,Any]]:
    with db.get_connection() as conn: ids=[row[0] for row in conn.execute("SELECT id FROM users ORDER BY id").fetchall()]
    return [item for uid in ids if (item:=public_user(db,uid)) is not None]


def create_user(db:Any,values:Dict[str,Any])->Optional[Dict[str,Any]]:
    username=str(values.get("username","")).strip();password=str(values.get("password",""));role=str(values.get("role","viewer")).strip();display_name=str(values.get("display_name") or username).strip()
    if not username or not password or role not in ROLE_PERMISSIONS or len(username)<3 or len(password)<8 or not display_name:return None
    with db.get_connection() as conn:
        try:
            cursor=conn.execute("INSERT INTO users (username,password_hash,role,display_name,full_name,email,avatar,phone,description,department,active,expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(username,generate_password_hash(password),role,display_name,str(values.get("full_name") or "").strip(),str(values.get("email") or "").strip(),str(values.get("avatar") or "").strip(),str(values.get("phone") or "").strip(),str(values.get("description") or "").strip(),str(values.get("department") or "").strip(),1 if values.get("active",True) else 0,values.get("expires_at") or None));user_id=int(cursor.lastrowid)
            if "permissions" in values:_store_exact_permissions(conn,user_id,values.get("permissions"))
            conn.commit()
        except sqlite3.IntegrityError:return None
    return public_user(db,user_id)


def update_user(db:Any,user_id:int,values:Dict[str,Any])->Optional[Dict[str,Any]]:
    allowed={"username","role","display_name","full_name","email","avatar","phone","description","department","active","expires_at"};changes={k:values[k] for k in allowed if k in values}
    if "username" in changes and not str(changes["username"]).strip():return None
    if "display_name" in changes and not str(changes["display_name"]).strip():return None
    if "role" in changes and changes["role"] not in ROLE_PERMISSIONS:return None
    if values.get("password"):
        password=str(values["password"])
        if len(password)<8:return None
        changes["password_hash"]=generate_password_hash(password)
    if not changes and "permissions" not in values:return None
    with db.get_connection() as conn:
        try:
            if changes:
                assignments=", ".join(f"{key}=?" for key in changes);cursor=conn.execute(f"UPDATE users SET {assignments} WHERE id=?",[*changes.values(),user_id])
                if cursor.rowcount==0:return None
            if "permissions" in values:_store_exact_permissions(conn,user_id,values.get("permissions"))
            conn.commit()
        except sqlite3.IntegrityError:return None
    return public_user(db,user_id)
