import React, { useEffect, useMemo, useState } from "react";
import { Save, UserRound, Info, ShieldCheck } from "lucide-react";
import { api, send } from "../../services/api";
import type { PermissionAction, PermissionMap, User } from "../../types";
import { Header, PanelTitle, Modal } from "../../components/Common";

const ACTIONS: { key: PermissionAction; label: string; help: string }[] = [
    { key: "view", label: "Visualizar", help: "Permite consultar a informação." },
    { key: "create", label: "Criar", help: "Permite adicionar novos registros." },
    { key: "edit", label: "Editar", help: "Permite alterar registros existentes." },
    { key: "delete", label: "Excluir", help: "Permite remover registros." },
    { key: "execute", label: "Executar", help: "Permite iniciar processos operacionais." },
    { key: "admin", label: "Administrar", help: "Permite alterar controles sensíveis do recurso." },
];
const RESOURCES = [
    ["dashboard", "Painel geral"], ["channels", "Canais"], ["playlists", "Playlists"], ["epg", "EPG/XMLTV"],
    ["sync", "Sincronização"], ["health", "Monitoramento"], ["settings", "Configurações"], ["users", "Usuários"],
    ["logs", "Logs"], ["maintenance", "Manutenção"], ["public_files", "Arquivos públicos"], ["system", "Sistema"],
] as const;

type UserForm = {
    username: string; password: string; role: User["role"]; display_name: string; full_name: string;
    email: string; avatar: string; phone: string; description: string; department: string;
    active: boolean; expires_at: string; permissions: PermissionMap;
};

const emptyPermissions = (): PermissionMap => ({});
const emptyForm = (): UserForm => ({ username: "", password: "", role: "viewer", display_name: "", full_name: "", email: "", avatar: "", phone: "", description: "", department: "", active: true, expires_at: "", permissions: emptyPermissions() });
const permissionMap = (user?: User | null): PermissionMap => user?.permissions || {};

export function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [editing, setEditing] = useState<User | null>(null);
    const [form, setForm] = useState<UserForm>(emptyForm());
    const [showPermissions, setShowPermissions] = useState(true);
    const load = () => api<User[]>("/api/v1/users").then(setUsers).catch(() => undefined);
    useEffect(() => { load(); }, []);

    const openCreate = () => { setEditing(null); setForm(emptyForm()); setShowPermissions(true); };
    const openEdit = (user: User) => {
        setEditing(user);
        setForm({
            username: user.username, password: "", role: user.role, display_name: user.display_name || user.username,
            full_name: user.full_name || "", email: user.email || "", avatar: user.avatar || "", phone: user.phone || "",
            description: user.description || "", department: user.department || "", active: Boolean(user.active ?? true),
            expires_at: user.expires_at || "", permissions: permissionMap(user),
        });
        setShowPermissions(true);
    };
    const setField = <K extends keyof UserForm>(key: K, value: UserForm[K]) => setForm((old) => ({ ...old, [key]: value }));
    const togglePermission = (resource: string, action: PermissionAction) => {
        setForm((old) => {
            const current = new Set(old.permissions[resource] || []);
            current.has(action) ? current.delete(action) : current.add(action);
            const permissions = { ...old.permissions };
            if (current.size) permissions[resource] = [...current]; else delete permissions[resource];
            return { ...old, permissions };
        });
    };
    const roleNote = useMemo(() => ({
        viewer: "Perfil-base de consulta. Sem permissões de escrita por padrão.",
        editor: "Perfil-base operacional. Permite edição de canais e execução do processamento.",
        admin: "Perfil-base administrativo. Possui acesso integral aos recursos.",
    }[form.role]), [form.role]);

    const save = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!form.username.trim() || (!editing && form.password.length < 8)) {
            alert("Informe o login e uma senha de pelo menos 8 caracteres no cadastro."); return;
        }
        const payload: Record<string, unknown> = {
            username: form.username.trim(), role: form.role, display_name: form.display_name.trim() || form.username.trim(),
            full_name: form.full_name.trim(), email: form.email.trim(), avatar: form.avatar.trim(), phone: form.phone.trim(),
            description: form.description.trim(), department: form.department.trim(), active: form.active, expires_at: form.expires_at || null,
            permissions: form.permissions,
        };
        if (form.password) payload.password = form.password;
        try {
            if (editing) await api(`/api/v1/users/${editing.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
            else await send("/api/v1/users", { ...payload, password: form.password });
            setForm(emptyForm()); setEditing(null); load();
        } catch { alert("Não foi possível salvar o usuário. Verifique os dados e suas permissões."); }
    };

    return <>
        <Header kicker="CONTROLE DE ACESSO" title="Usuários" description="Contas, perfis e permissões detalhadas por recurso e ação." />
        <div className="panel">
            <PanelTitle kicker="CONTAS" title={editing ? `Editando ${editing.username}` : "Novo usuário"} />
            <form className="user-form" onSubmit={save}>
                <div className="form-help"><Info size={15} /><span><b>Campos obrigatórios:</b> login, senha no cadastro, perfil, nome de exibição e status. Os demais são opcionais.</span></div>
                <div className="user-form-grid">
                    <label>Login *<input required value={form.username} onChange={(e) => setField("username", e.target.value)} /></label>
                    <label>Nome de exibição *<input required value={form.display_name} onChange={(e) => setField("display_name", e.target.value)} placeholder="Nome mostrado na interface" /></label>
                    <label>Senha {editing ? "(opcional)" : "*"}<input type="password" minLength={8} required={!editing} value={form.password} onChange={(e) => setField("password", e.target.value)} placeholder={editing ? "Deixe vazio para manter" : "Mínimo de 8 caracteres"} /></label>
                    <label>Perfil-base *<select value={form.role} onChange={(e) => setField("role", e.target.value as User["role"])}><option value="viewer">Viewer</option><option value="editor">Editor</option><option value="admin">Admin</option></select></label>
                    <label>Nome completo<input value={form.full_name} onChange={(e) => setField("full_name", e.target.value)} /></label>
                    <label>E-mail<input type="email" value={form.email} onChange={(e) => setField("email", e.target.value)} /></label>
                    <label>Telefone<input value={form.phone} onChange={(e) => setField("phone", e.target.value)} /></label>
                    <label>Departamento/grupo<input value={form.department} onChange={(e) => setField("department", e.target.value)} /></label>
                    <label>Avatar (URL)<input value={form.avatar} onChange={(e) => setField("avatar", e.target.value)} placeholder="Opcional" /></label>
                    <label>Expiração<input type="datetime-local" value={form.expires_at ? form.expires_at.slice(0, 16) : ""} onChange={(e) => setField("expires_at", e.target.value)} /></label>
                    <label className="checkbox-label"><input type="checkbox" checked={form.active} onChange={(e) => setField("active", e.target.checked)} /> Conta ativa</label>
                </div>
                <label>Descrição/observação<textarea value={form.description} onChange={(e) => setField("description", e.target.value)} rows={3} /></label>
                <div className="permission-help"><ShieldCheck size={17} /><div><b>Permissões detalhadas</b><p>{roleNote} As permissões abaixo são adicionais ao perfil-base; desmarcar uma permissão de um perfil-base não a remove nesta primeira versão. A próxima camada poderá suportar negações explícitas.</p></div></div>
                <button type="button" className="text-button" onClick={() => setShowPermissions(!showPermissions)}>{showPermissions ? "Ocultar matriz" : "Mostrar matriz"}</button>
                {showPermissions && <div className="permission-table-wrap"><table className="permission-table"><thead><tr><th>Recurso</th>{ACTIONS.map((action) => <th key={action.key} title={action.help}>{action.label}</th>)}</tr></thead><tbody>{RESOURCES.map(([key, label]) => <tr key={key}><td><b>{label}</b></td>{ACTIONS.map((action) => <td key={action.key}><input type="checkbox" aria-label={`${label}: ${action.label}`} checked={(form.permissions[key] || []).includes(action.key)} onChange={() => togglePermission(key, action.key)} /></td>)}</tr>)}</tbody></table></div>}
                <div className="modal-actions"><button className="button primary"><Save size={15} /> {editing ? "Salvar alterações" : "Criar usuário"}</button>{editing && <button type="button" className="button subtle" onClick={openCreate}>Cancelar edição</button>}</div>
            </form>
        </div>
        <div className="panel">
            <PanelTitle kicker="USUÁRIOS" title="Contas existentes" badge={`${users.length} conta(s)`} />
            <div className="table-scroll"><table><thead><tr><th>ID</th><th>Usuário</th><th>Nome</th><th>Perfil</th><th>Status</th><th>Criação</th><th>Ação</th></tr></thead><tbody>{users.map((u) => <tr key={u.id}><td>{u.id}</td><td><b>{u.username}</b></td><td>{u.display_name || "-"}</td><td><span className="tag">{u.role}</span></td><td>{u.active === false || u.active === 0 ? "Inativo" : "Ativo"}</td><td>{u.created_at || "-"}</td><td><button className="text-button" onClick={() => openEdit(u)}><UserRound size={14} /> Editar</button></td></tr>)}</tbody></table></div>
        </div>
    </>;
}
