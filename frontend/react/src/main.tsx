import { useEffect, useState } from "react";
import {
    Boxes,
    ChevronLeft,
    ChevronRight,
    CircleGauge,
    Copy,
    LayoutDashboard,
    ListVideo,
    LogOut,
    Menu,
    MoreVertical,
    Play,
    Power,
    RotateCcw,
    RefreshCw,
    Save,
    Settings,
    ShieldCheck,
    SlidersHorizontal,
    Square,
    UserRound,
    Users,
    Wifi,
    X,
    Zap,
} from "lucide-react";
import { createRoot } from "react-dom/client";
import Hls from "hls.js";
import "./styles.scss";

type User = {
    id: number;
    username: string;
    role: "admin" | "editor" | "viewer";
    created_at?: string;
};
type Channel = {
    id: number;
    name: string;
    url: string;
    logo?: string;
    metadata?: string;
    tvg_id?: string;
    group_title?: string;
    country?: string;
    state?: string;
    city?: string;
    category: string;
    status: string;
    latency_ms?: number;
    auto_remove_if_offline?: number;
    playlist?: string;
    xmltv_file?: string;
};
type Manifest = {
    m3u_name: string;
    m3u_url: string;
    xml_name?: string;
    xml_url: string;
    total: number;
};
type Status = {
    status: string;
    total_canais: number;
    canais_online: number;
    canais_offline: number;
    canais_desconhecidos?: number;
    ultimo_log: string;
    logs: { timestamp: string; level: string; message: string }[];
    log_count: number;
};

const api = async <T,>(url: string, options?: RequestInit) => {
    const response = await fetch(url, options);
    if (!response.ok) throw Error(String(response.status));
    return response.json() as Promise<T>;
};
const send = <T = unknown,>(url: string, body?: unknown) =>
    api<T>(url, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
    });
const canEdit = (user: User) => user.role !== "viewer";
const nav = [
    { path: "/", label: "Painel geral", icon: LayoutDashboard },
    { path: "/channels", label: "Canais e editor", icon: Boxes },
    { path: "/playlists", label: "Listas publicadas", icon: ListVideo },
    { path: "/users", label: "Usuários", icon: Users, admin: true },
    { path: "/settings", label: "Configurações", icon: Settings, admin: true },
];

function Shell({ user, children }: { user: User; children: React.ReactNode }) {
    const [collapsed, setCollapsed] = useState(
        localStorage.getItem("sidebar-collapsed") === "true",
    );
    const path = window.location.pathname;
    const [profileOpen, setProfileOpen] = useState(false);
    const [adminOpen, setAdminOpen] = useState(false);
    return (
        <div className={`app-shell ${collapsed ? "is-collapsed" : ""}`}>
            <aside className="sidebar">
                <div className="brand">
                    <span className="brand-mark">M3</span>
                    <span className="brand-name">M3U ARCHITECT</span>
                </div>
                <button
                    className="icon-button sidebar-toggle"
                    onClick={() => {
                        setCollapsed(!collapsed);
                        localStorage.setItem("sidebar-collapsed", String(!collapsed));
                    }}
                    title="Recolher menu"
                >
                    <Menu size={18} />
                </button>
                <nav>
                    {nav
                        .filter((n) => !n.admin || user.role === "admin")
                        .map((n) => {
                            const Icon = n.icon;
                            return (
                                <a
                                    className={path === n.path ? "active" : ""}
                                    href={n.path}
                                    key={n.path}
                                >
                                    <Icon size={18} />
                                    <span>{n.label}</span>
                                </a>
                            );
                        })}
                </nav>
                <a className="logout" href="/logout">
                    <LogOut size={17} />
                    <span>Sair</span>
                </a>
            </aside>
            <main className="main-content">
                <header className="topbar">
                    <div>
                        <span className="kicker">CENTRO DE OPERAÇÕES</span>
                        <p>Olá, {user.username}</p>
                    </div>
                    <div className="account-actions">
                        <button className="account-button" onClick={() => setProfileOpen(true)} title="Editar perfil">
                            <UserRound size={15} /> {user.username}
                        </button>
                        {user.role === "admin" && <div className="admin-menu-wrap">
                            <button className="icon-button" onClick={() => setAdminOpen(!adminOpen)} title="Opções administrativas"><MoreVertical size={18} /></button>
                            {adminOpen && <div className="admin-menu">
                                <button onClick={() => api("/api/admin/restart", { method: "POST" }).then(() => setTimeout(() => window.location.reload(), 1200))}><RotateCcw size={15} /> Reiniciar servidor</button>
                                <button onClick={() => confirm("Desligar o servidor agora?") && api("/api/admin/shutdown", { method: "POST" })}><Power size={15} /> Desligar servidor</button>
                                <button onClick={() => setProfileOpen(true)}><UserRound size={15} /> Editar perfil</button>
                            </div>}
                        </div>}
                        <span className="role-chip"><ShieldCheck size={14} /> {user.role}</span>
                    </div>
                </header>
                {children}
            </main>
            {profileOpen && <ProfileModal user={user} close={() => setProfileOpen(false)} />}
        </div>
    );
}
function ProfileModal({ user, close }: { user: User; close: () => void }) {
    const [form, setForm] = useState({ username: user.username, password: "" });
    const save = () => api("/api/profile", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) }).then(() => { close(); window.location.reload(); }).catch(() => alert("Não foi possível atualizar o perfil."));
    return <Modal title="Editar perfil" close={close}><label>Nome de usuário<input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /></label><label>Nova senha<input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="Opcional" /></label><div className="modal-actions"><button className="button subtle" onClick={close}>Cancelar</button><button className="button primary" onClick={save}><Save size={15} /> Salvar perfil</button></div></Modal>;
}
function Login() {
    return (
        <main className="login-screen">
            <form className="login-card" method="post" action="/login">
                <span className="brand-mark">M3</span>
                <p className="kicker">M3U ARCHITECT</p>
                <h1>Controle sua grade.</h1>
                <p className="muted">
                    Auditoria, conectividade e distribuição em um só lugar.
                </p>
                <label>
                    Usuário
                    <input name="username" required autoFocus />
                </label>
                <label>
                    Senha
                    <input name="password" type="password" required />
                </label>
                <button className="button primary full">
                    <Zap size={16} /> Entrar no sistema
                </button>
            </form>
        </main>
    );
}
function Header({
    kicker,
    title,
    description,
    children,
}: {
    kicker: string;
    title: string;
    description: string;
    children?: React.ReactNode;
}) {
    return (
        <header className="page-heading">
            <div>
                <span className="kicker">{kicker}</span>
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
            {children}
        </header>
    );
}
function PanelTitle({
    kicker,
    title,
    badge,
}: {
    kicker: string;
    title: string;
    badge?: string;
}) {
    return (
        <div className="panel-title">
            <div>
                <span className="kicker">{kicker}</span>
                <h2>{title}</h2>
            </div>
            {badge && <span className="panel-badge">{badge}</span>}
        </div>
    );
}
function Empty({ text }: { text: string }) {
    return <div className="empty">{text}</div>;
}
function Modal({
    title,
    children,
    close,
}: {
    title: string;
    children: React.ReactNode;
    close: () => void;
}) {
    return (
        <div
            className="modal-backdrop"
            onMouseDown={(e) => e.target === e.currentTarget && close()}
        >
            <div className="modal">
                <button className="icon-button modal-close" onClick={close}>
                    <X size={18} />
                </button>
                <h2>{title}</h2>
                {children}
            </div>
        </div>
    );
}

function Dashboard({ user }: { user: User }) {
    const [data, setData] = useState<Status | null>(null);
    const load = () =>
        api<Status>("/api/status")
            .then(setData)
            .catch(() => undefined);
    useEffect(() => {
        load();
        const t = setInterval(load, 3000);
        return () => clearInterval(t);
    }, []);
    const total = data?.total_canais || 0;
    const online = data?.canais_online || 0;
    const offline = data?.canais_offline || 0;
    const unknown = data?.canais_desconhecidos || Math.max(total - online - offline, 0);
    const hasHealthResult = online + offline > 0;
    const rate = total && hasHealthResult ? Math.round((online / total) * 100) : null;
    const running =
        data?.status === "Executando..." || data?.status === "Pausado";
    const action = (url: string) => send(url).then(load);
    return (
        <>
            <Header
                kicker="MONITORAMENTO AO VIVO"
                title="Painel geral"
                description="Visão operacional da auditoria, conectividade e geração das listas."
            >
                {canEdit(user) && (
                    <div className="actions">
                        <button
                            className="button primary"
                            disabled={running}
                            onClick={() => action("/api/v1/sync")}
                        >
                            <Zap size={15} /> Iniciar sincronização
                        </button>
                        <button
                            className="button subtle"
                            disabled={!running}
                            onClick={() => action("/api/v1/sync/pause")}
                        >
                            {data?.status === "Pausado" ? "Retomar" : "Pausar"}
                        </button>
                        <button
                            className="button danger"
                            disabled={!running}
                            onClick={() =>
                                confirm("Interromper a execução atual?") &&
                                action("/api/v1/sync/stop")
                            }
                        >
                            <Square size={14} /> Interromper
                        </button>
                    </div>
                )}
            </Header>
            <section className="metric-grid">
                <Metric
                    label="Status do processo"
                    value={data?.status || "Carregando"}
                    detail={data?.ultimo_log || "Aguardando dados"}
                    tone="blue"
                />
                <Metric
                    label="Canais catalogados"
                    value={total}
                    detail="base atual"
                    tone="blue"
                />
                <Metric
                    label="Online"
                    value={online}
                    detail={rate === null ? "verificando" : `${rate}% da base`}
                    tone="green"
                />
                <Metric
                    label="Offline / removidos"
                    value={offline}
                    detail="última verificação"
                    tone="red"
                />
            </section>
            <section className="split-grid">
                <div className="panel health-panel">
                    <PanelTitle
                        kicker="DISTRIBUIÇÃO"
                        title="Saúde dos canais"
                        badge="AO VIVO"
                    />
                    <div className="health-content">
                        <div
                            className="donut"
                            style={{ "--progress": `${(rate || 0) * 3.6}deg` } as React.CSSProperties}
                        >
                            <strong>{rate === null ? "..." : `${rate}%`}</strong>
                            <small>{rate === null ? "verificando" : "online"}</small>
                        </div>
                        <div className="legend">
                            <Legend label="Online" value={online} color="green" />
                            <Legend label="Offline" value={offline} color="red" />
                            <Legend
                                label="Não verificado"
                                value={unknown}
                                color="muted"
                            />
                        </div>
                    </div>
                </div>
                <div className="panel">
                    <PanelTitle
                        kicker="ATIVIDADE"
                        title="O que está acontecendo"
                        badge={`${data?.log_count || 0} eventos`}
                    />
                    <div className="activity-list">
                        {data?.logs?.slice(0, 12).map((l) => (
                            <div
                                className={`activity ${l.level}`}
                                key={`${l.timestamp}-${l.message}`}
                            >
                                <time>{l.timestamp.slice(11)}</time>
                                <span>{l.message}</span>
                            </div>
                        )) || <Empty text="Nenhuma atividade registrada." />}
                    </div>
                </div>
            </section>
            <div className="panel">
                <PanelTitle
                    kicker="PIPELINE"
                    title="Progresso da operação"
                    badge={data?.status || "Ocioso"}
                />
                <div className="progress-track">
                    <span
                        style={{
                            width:
                                data?.status === "Concluido" ? "100%" : running ? "62%" : "12%",
                        }}
                    />
                </div>
                <div className="progress-labels">
                    <span>Leitura</span>
                    <span>Verificação</span>
                    <span>Particionamento</span>
                    <span>Concluído</span>
                </div>
            </div>
        </>
    );
}
function Metric({
    label,
    value,
    detail,
    tone,
}: {
    label: string;
    value: string | number;
    detail: string;
    tone: string;
}) {
    return (
        <article className={`metric metric-${tone}`}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
        </article>
    );
}
function Legend({
    label,
    value,
    color,
}: {
    label: string;
    value: number;
    color: string;
}) {
    return (
        <div className="legend-row">
            <i className={`dot ${color}`} />
            <span>{label}</span>
            <b>{value}</b>
        </div>
    );
}

function Channels({ user }: { user: User }) {
    const [channels, setChannels] = useState<Channel[]>([]);
    const [query, setQuery] = useState({
        search: "",
        country: "todos",
        category: "todos",
        status: "todos",
        sort: "id",
        direction: "asc",
    });
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);
    const [selected, setSelected] = useState<number[]>([]);
    const [editing, setEditing] = useState<Channel | null>(null);
    const [builder, setBuilder] = useState(false);
    const load = () =>
        api<Channel[]>(`/api/v1/channels?${new URLSearchParams(query)}`)
            .then((d) => {
                setChannels(d);
                setPage(1);
                setSelected([]);
            })
            .catch(() => undefined);
    useEffect(() => {
        const t = setTimeout(load, query.search ? 300 : 0);
        return () => clearTimeout(t);
    }, [
        query.search,
        query.country,
        query.category,
        query.status,
        query.sort,
        query.direction,
    ]);
    const totalPages = Math.max(1, Math.ceil(channels.length / pageSize));
    const visible = channels.slice((page - 1) * pageSize, page * pageSize);
    const all =
        visible.length > 0 && visible.every((c) => selected.includes(c.id));
    const patch = (url: string, body: unknown) =>
        api(url, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        }).then(load);
    const updateQuery = (key: keyof typeof query, value: string) =>
        setQuery({ ...query, [key]: value });
    return (
        <>
            <Header
                kicker="CATÁLOGO"
                title="Canais e editor"
                description="Filtre, audite e ajuste os metadados da sua grade."
            >
                <button className="button subtle" onClick={load}>
                    <RefreshCw size={15} /> Atualizar
                </button>
            </Header>
            <div className="panel table-panel">
                <div className="toolbar">
                    <div className="search">
                        <SlidersHorizontal size={16} />
                        <input
                            placeholder="Pesquisar nome, URL, grupo, EPG ou local..."
                            value={query.search}
                            onChange={(e) => updateQuery("search", e.target.value)}
                        />
                    </div>
                    <select
                        value={query.country}
                        onChange={(e) => updateQuery("country", e.target.value)}
                    >
                        <option value="todos">Todos os países</option>
                        <option>Brasil</option>
                        <option>Portugal</option>
                        <option>Estados Unidos</option>
                    </select>
                    <select
                        value={query.category}
                        onChange={(e) => updateQuery("category", e.target.value)}
                    >
                        <option value="todos">Todas as categorias</option>
                        <option value="tv">TV</option>
                        <option value="vod">VOD</option>
                        <option value="series">Séries</option>
                        <option value="radio">Rádio</option>
                    </select>
                    <select
                        value={query.status}
                        onChange={(e) => updateQuery("status", e.target.value)}
                    >
                        <option value="todos">Todos os status</option>
                        <option value="online">Apenas online</option>
                        <option value="offline">Apenas offline</option>
                    </select>
                    <select
                        value={query.sort}
                        onChange={(e) => updateQuery("sort", e.target.value)}
                    >
                        <option value="id">Ordenar por inclusão</option>
                        <option value="name">Nome</option>
                        <option value="country">País</option>
                        <option value="category">Categoria</option>
                        <option value="status">Status</option>
                        <option value="latency_ms">Latência</option>
                    </select>
                    <select
                        value={query.direction}
                        onChange={(e) => updateQuery("direction", e.target.value)}
                    >
                        <option value="asc">Crescente</option>
                        <option value="desc">Decrescente</option>
                    </select>
                </div>
                <div className="editor-actions">
                    <label>
                        <input
                            type="checkbox"
                            checked={all}
                            onChange={(e) =>
                                setSelected(
                                    e.target.checked
                                        ? [...new Set([...selected, ...visible.map((c) => c.id)])]
                                        : selected.filter(
                                            (id) => !visible.some((c) => c.id === id),
                                        ),
                                )
                            }
                        />{" "}
                        Selecionar página
                    </label>
                    <span className="muted-text">
                        {selected.length} selecionado(s) de {channels.length}
                    </span>
                    <div className="pagination">
                        <button
                            className="icon-button"
                            disabled={page === 1}
                            onClick={() => setPage(page - 1)}
                        >
                            <ChevronLeft size={17} />
                        </button>
                        <span>
                            Página {page} de {totalPages}
                        </span>
                        <button
                            className="icon-button"
                            disabled={page === totalPages}
                            onClick={() => setPage(page + 1)}
                        >
                            <ChevronRight size={17} />
                        </button>
                    </div>
                    <input
                        className="page-size"
                        type="number"
                        min="1"
                        value={pageSize}
                        onChange={(e) =>
                            setPageSize(Math.max(1, Number(e.target.value) || 1))
                        }
                    />
                    <button
                        className="button primary"
                        disabled={!selected.length || !canEdit(user)}
                        onClick={() => setBuilder(true)}
                    >
                        Criar lista com seleção
                    </button>
                </div>
                <div className="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>
                                    <input
                                        type="checkbox"
                                        checked={all}
                                        onChange={(e) =>
                                            setSelected(
                                                e.target.checked ? visible.map((c) => c.id) : [],
                                            )
                                        }
                                    />
                                </th>
                                <th>Status</th>
                                <th>Ch. No.</th>
                                <th>Logo</th>
                                <th>Channel Name</th>
                                <th>Playlist</th>
                                <th>Group Title</th>
                                <th>XMLTV File</th>
                                <th>XMLTV ID</th>
                                <th>Latência</th>
                                <th>Remover OFF</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {visible.map((c) => (
                                <tr key={c.id}>
                                    <td>
                                        <input
                                            type="checkbox"
                                            checked={selected.includes(c.id)}
                                            onChange={(e) =>
                                                setSelected(
                                                    e.target.checked
                                                        ? [...selected, c.id]
                                                        : selected.filter((id) => id !== c.id),
                                                )
                                            }
                                        />
                                    </td>
                                    <td>
                                        <button
                                            className={`status-dot ${c.status}`}
                                            disabled={!canEdit(user)}
                                            onClick={() =>
                                                patch(`/api/v1/channels/${c.id}/status`, {
                                                    status: c.status === "online" ? "offline" : "online",
                                                })
                                            }
                                        />
                                    </td>
                                    <td>{c.id}</td>
                                    <td>
                                        <span className="channel-logo">
                                            {c.logo ? (
                                                <img
                                                    src={c.logo}
                                                    onError={(e) => {
                                                        e.currentTarget.style.display = "none";
                                                    }}
                                                />
                                            ) : (
                                                <Wifi size={14} />
                                            )}
                                        </span>
                                    </td>
                                    <td className="channel-name"><b>{c.name}</b></td>
                                    <td>{c.playlist || "-"}</td>
                                    <td>{c.group_title || "-"}</td>
                                    <td>{c.xmltv_file || "-"}</td>
                                    <td>{c.tvg_id || "-"}</td>
                                    <td>{c.latency_ms || 0} ms</td>
                                    <td>
                                        <input
                                            type="checkbox"
                                            checked={Boolean(c.auto_remove_if_offline)}
                                            disabled={!canEdit(user)}
                                            onChange={(e) =>
                                                patch(`/api/v1/channels/${c.id}/autoremove`, {
                                                    auto_remove_if_offline: e.target.checked ? 1 : 0,
                                                })
                                            }
                                        />
                                    </td>
                                    <td>
                                        {canEdit(user) && (
                                            <button
                                                className="text-button"
                                                onClick={() => setEditing(c)}
                                            >
                                                Editar
                                            </button>
                                        )}
                                        <button
                                            className="icon-button"
                                            title="Assistir"
                                            onClick={() =>
                                                dispatchEvent(
                                                    new CustomEvent("play-channel", { detail: c }),
                                                )
                                            }
                                        >
                                            <Play size={14} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {!channels.length && <Empty text="Nenhum canal encontrado." />}
            </div>
            {editing && (
                <ChannelEditor
                    channel={editing}
                    close={() => setEditing(null)}
                    saved={() => {
                        setEditing(null);
                        load();
                    }}
                />
            )}
            {builder && (
                <PlaylistBuilder ids={selected} close={() => setBuilder(false)} />
            )}
        </>
    );
}

function ChannelEditor({
    channel,
    close,
    saved,
}: {
    channel: Channel;
    close: () => void;
    saved: () => void;
}) {
    const [form, setForm] = useState(channel);
    const set = (key: keyof Channel, value: string | number) =>
        setForm({ ...form, [key]: value });
    const submit = (e: React.FormEvent) => {
        e.preventDefault();
        api(`/api/v1/channels/${channel.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(form),
        })
            .then(saved)
            .catch(() => alert("Não foi possível salvar o canal."));
    };
    return (
        <Modal title="Editar canal completo" close={close}>
            <form className="edit-form" onSubmit={submit}>
                <div className="form-grid">
                    {(
                        [
                            "name",
                            "url",
                            "logo",
                            "tvg_id",
                            "group_title",
                            "country",
                            "state",
                            "city",
                        ] as const
                    ).map((k) => (
                        <label key={k}>
                            {k === "url" ? "URL do stream" : k}
                            <input
                                required={k === "name" || k === "url"}
                                value={String(form[k] || "")}
                                onChange={(e) => set(k, e.target.value)}
                            />
                        </label>
                    ))}
                </div>
                <label>
                    Categoria
                    <select
                        value={form.category}
                        onChange={(e) => set("category", e.target.value)}
                    >
                        <option value="tv">TV</option>
                        <option value="vod">VOD</option>
                        <option value="series">Séries</option>
                        <option value="radio">Rádio</option>
                        <option value="outros">Outros</option>
                    </select>
                </label>
                <label>
                    Status
                    <select
                        value={form.status}
                        onChange={(e) => set("status", e.target.value)}
                    >
                        <option value="online">Online</option>
                        <option value="offline">Offline</option>
                        <option value="desconhecido">Desconhecido</option>
                    </select>
                </label>
                <label>
                    Metadados M3U
                    <textarea
                        rows={4}
                        value={form.metadata || ""}
                        onChange={(e) => set("metadata", e.target.value)}
                    />
                </label>
                <label>
                    <input
                        type="checkbox"
                        checked={Boolean(form.auto_remove_if_offline)}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                auto_remove_if_offline: e.target.checked ? 1 : 0,
                            })
                        }
                    />{" "}
                    Remover automaticamente se ficar offline
                </label>
                <div className="modal-actions">
                    <button type="button" className="button subtle" onClick={close}>
                        Cancelar
                    </button>
                    <button className="button primary">
                        <Save size={15} /> Salvar canal
                    </button>
                </div>
            </form>
        </Modal>
    );
}
function PlaylistBuilder({ ids, close }: { ids: number[]; close: () => void }) {
    const [form, setForm] = useState({
        name: "",
        sort: "name",
        direction: "asc",
        limit: "",
        status: "online",
        country: "todos",
        category: "todos",
        group_title: "",
    });
    const [result, setResult] = useState("");
    const generate = () =>
        send<{ manifestos?: Manifest[] }>("/api/v1/playlists/generate", {
            ids,
            ...form,
            limit: form.limit || undefined,
        })
            .then((d) => {
                setResult(`${d.manifestos?.length || 0} arquivo(s) gerado(s).`);
                dispatchEvent(new CustomEvent("playlists-updated"));
            })
            .catch(() => setResult("Falha ao gerar a lista."));
    return (
        <Modal title="Criar lista M3U personalizada" close={close}>
            <p className="muted-text">{ids.length} canal(is) selecionado(s).</p>
            <div className="form-grid">
                <label>
                    Nome da lista
                    <input
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        placeholder="Ex.: canais-favoritos"
                    />
                </label>
                <label>
                    Ordenar por
                    <select
                        value={form.sort}
                        onChange={(e) => setForm({ ...form, sort: e.target.value })}
                    >
                        <option value="name">Nome</option>
                        <option value="country">País</option>
                        <option value="group_title">Grupo</option>
                        <option value="category">Categoria</option>
                        <option value="latency_ms">Latência</option>
                    </select>
                </label>
                <label>
                    Direção
                    <select
                        value={form.direction}
                        onChange={(e) => setForm({ ...form, direction: e.target.value })}
                    >
                        <option value="asc">Crescente</option>
                        <option value="desc">Decrescente</option>
                    </select>
                </label>
                <label>
                    Canais por arquivo
                    <input
                        type="number"
                        min="1"
                        value={form.limit}
                        onChange={(e) => setForm({ ...form, limit: e.target.value })}
                        placeholder="Padrão"
                    />
                </label>
                <label>
                    Status
                    <select
                        value={form.status}
                        onChange={(e) => setForm({ ...form, status: e.target.value })}
                    >
                        <option value="online">Somente online</option>
                        <option value="todos">Todos</option>
                    </select>
                </label>
                <label>
                    País
                    <input
                        value={form.country}
                        onChange={(e) => setForm({ ...form, country: e.target.value })}
                    />
                </label>
                <label>
                    Categoria
                    <select
                        value={form.category}
                        onChange={(e) => setForm({ ...form, category: e.target.value })}
                    >
                        <option value="todos">Todas</option>
                        <option value="tv">TV</option>
                        <option value="vod">VOD</option>
                        <option value="series">Séries</option>
                        <option value="radio">Rádio</option>
                    </select>
                </label>
                <label>
                    Grupo
                    <input
                        value={form.group_title}
                        onChange={(e) => setForm({ ...form, group_title: e.target.value })}
                    />
                </label>
            </div>
            <button className="button primary" onClick={generate}>
                <ListVideo size={15} /> Gerar playlist
            </button>
            {result && <p className="muted-text">{result}</p>}
        </Modal>
    );
}
function Playlists() {
    const [items, setItems] = useState<Manifest[]>([]);
    const [status, setStatus] = useState("Aguardando");
    const [selected, setSelected] = useState<string[]>([]);
    const [editing, setEditing] = useState(false);
    const [baseUrl, setBaseUrl] = useState("");
    const [message, setMessage] = useState("");
    const load = () =>
        api<{ status: string; manifestos: Manifest[] }>("/api/v1/playlists")
            .then((d) => {
                setStatus(d.status);
                setItems(d.manifestos || []);
                setSelected([]);
            })
            .catch(() => undefined);
    useEffect(() => {
        load();
        const t = setInterval(load, 10000);
        return () => clearInterval(t);
    }, []);
    const all = items.length > 0 && selected.length === items.length;
    const remove = () => {
        if (
            !selected.length ||
            !confirm(`Excluir ${selected.length} lista(s) e seus arquivos XML?`)
        )
            return;
        api("/api/v1/playlists", {
            method: "DELETE",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ m3u_names: selected }),
        })
            .then(() => {
                setMessage("Listas excluídas.");
                load();
            })
            .catch(() => setMessage("Não foi possível excluir as listas."));
    };
    const openEditor = () => {
        api<Record<string, string | number>>("/api/config")
            .then((c) => {
                setBaseUrl(String(c.BASE_URL || ""));
                setEditing(true);
            })
            .catch(() => setMessage("Não foi possível carregar a configuração."));
    };
    const saveUrl = () =>
        api("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ BASE_URL: baseUrl }),
        })
            .then(() => {
                setEditing(false);
                setMessage("Endereço público atualizado.");
                load();
            })
            .catch(() => setMessage("Não foi possível salvar o endereço."));
    return (
        <>
            <Header
                kicker="ENTREGA"
                title="Listas publicadas"
                description="Arquivos M3U e XMLTV criados pelo processamento atual."
            >
                <span className="live-status">
                    <i /> {status}
                </span>
            </Header>
            <div className="panel table-panel">
                <div className="panel-title">
                    <div>
                        <span className="kicker">ARQUIVOS PUBLICADOS</span>
                        <h2>Links disponíveis</h2>
                    </div>
                    <div className="actions">
                        <button className="button subtle" onClick={load}>
                            <RefreshCw size={15} /> Atualizar
                        </button>
                        <button
                            className="button subtle"
                            disabled={!selected.length}
                            onClick={remove}
                        >
                            Excluir selecionadas
                        </button>
                        <button className="button primary" onClick={openEditor}>
                            <Settings size={15} /> Editar endereço
                        </button>
                    </div>
                </div>
                <div className="editor-actions">
                    <label>
                        <input
                            type="checkbox"
                            checked={all}
                            onChange={(e) =>
                                setSelected(
                                    e.target.checked ? items.map((i) => i.m3u_name) : [],
                                )
                            }
                        />{" "}
                        Selecionar todas
                    </label>
                    <span className="muted-text">{selected.length} selecionada(s)</span>
                    {message && <span className="muted-text">{message}</span>}
                </div>
                <div className="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>Selecionar</th>
                                <th>Lista</th>
                                <th>Canais</th>
                                <th>M3U</th>
                                <th>EPG XMLTV</th>
                                <th>Atalhos</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items.map((i) => (
                                <tr key={i.m3u_name}>
                                    <td>
                                        <input
                                            type="checkbox"
                                            checked={selected.includes(i.m3u_name)}
                                            onChange={(e) =>
                                                setSelected(
                                                    e.target.checked
                                                        ? [...selected, i.m3u_name]
                                                        : selected.filter((n) => n !== i.m3u_name),
                                                )
                                            }
                                        />
                                    </td>
                                    <td>
                                        <b>{i.m3u_name}</b>
                                    </td>
                                    <td>{i.total}</td>
                                    <td>
                                        <a href={i.m3u_url} target="_blank">
                                            {i.m3u_url}
                                        </a>
                                    </td>
                                    <td>
                                        <a href={i.xml_url} target="_blank">
                                            {i.xml_url}
                                        </a>
                                    </td>
                                    <td>
                                        <button
                                            className="icon-button"
                                            title="Copiar M3U"
                                            onClick={() => navigator.clipboard?.writeText(i.m3u_url)}
                                        >
                                            <Copy size={15} />
                                        </button>
                                        <button
                                            className="icon-button"
                                            title="Copiar XMLTV"
                                            onClick={() => navigator.clipboard?.writeText(i.xml_url)}
                                        >
                                            <Copy size={15} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {!items.length && <Empty text="Nenhuma lista criada nesta sessão." />}
            </div>
            {editing && (
                <Modal
                    title="Editar endereço público das listas"
                    close={() => setEditing(false)}
                >
                    <p className="muted-text">
                        Esse endereço é usado pelos links M3U e XMLTV publicados.
                    </p>
                    <label>
                        URL base pública
                        <input
                            value={baseUrl}
                            onChange={(e) => setBaseUrl(e.target.value)}
                            placeholder="http://127.0.0.1:5000"
                        />
                    </label>
                    <div className="modal-actions">
                        <button className="button subtle" onClick={() => setEditing(false)}>
                            Cancelar
                        </button>
                        <button className="button primary" onClick={saveUrl}>
                            <Save size={15} /> Salvar endereço
                        </button>
                    </div>
                </Modal>
            )}
        </>
    );
}
function SettingsPage() {
    const [config, setConfig] = useState<Record<string, string | number>>({});
    const [saved, setSaved] = useState(false);
    useEffect(() => {
        api<Record<string, string | number>>("/api/config")
            .then(setConfig)
            .catch(() => undefined);
    }, []);
    const set = (k: string, v: string) => setConfig({ ...config, [k]: v });
    const save = () =>
        api("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config),
        }).then(() => {
            setSaved(true);
            setTimeout(() => setSaved(false), 2500);
        });
    return (
        <>
            <Header
                kicker="SISTEMA"
                title="Configurações"
                description="Parâmetros de execução, distribuição e integrações."
            />
            <div className="panel settings-panel">
                <PanelTitle kicker="AMBIENTE" title="Parâmetros operacionais" />
                <div className="form-grid">
                    <label>
                        Modo de automação
                        <select
                            value={String(config.SCHEDULE_MODE || "DISABLED")}
                            onChange={(e) => set("SCHEDULE_MODE", e.target.value)}
                        >
                            <option value="DISABLED">Desativado (manual)</option>
                            <option value="INTERVAL">Por intervalo regular</option>
                            <option value="CRON">Horário fixo diário</option>
                        </select>
                    </label>
                    <label>
                        Tempo (horas ou HH:MM)
                        <input
                            value={String(
                                config.SCHEDULE_MODE === "INTERVAL"
                                    ? config.SCHEDULE_INTERVAL_HOURS || ""
                                    : config.SCHEDULE_CRON_TIME || "",
                            )}
                            onChange={(e) =>
                                set(
                                    config.SCHEDULE_MODE === "INTERVAL"
                                        ? "SCHEDULE_INTERVAL_HOURS"
                                        : "SCHEDULE_CRON_TIME",
                                    e.target.value,
                                )
                            }
                        />
                    </label>
                    <label>
                        URL do menu
                        <input
                            value={String(config.BASE_URL || "")}
                            onChange={(e) => set("BASE_URL", e.target.value)}
                        />
                    </label>
                    <label>
                        URL dos links públicos
                        <input
                            value={String(config.PUBLIC_BASE_URL || "")}
                            onChange={(e) => set("PUBLIC_BASE_URL", e.target.value)}
                        />
                    </label>
                    <label>
                        Porta do menu
                        <input
                            type="number"
                            value={String(config.WEB_PORT || "")}
                            onChange={(e) => set("WEB_PORT", e.target.value)}
                        />
                    </label>
                    <label>
                        Porta dos links
                        <input
                            type="number"
                            value={String(config.PUBLIC_PORT || "")}
                            onChange={(e) => set("PUBLIC_PORT", e.target.value)}
                        />
                    </label>
                    <label>
                        Capacidade máxima por lista
                        <input
                            type="number"
                            value={String(config.MAX_CHANNELS_PER_FILE || "")}
                            onChange={(e) => set("MAX_CHANNELS_PER_FILE", e.target.value)}
                        />
                    </label>
                    <label>
                        Concorrência de verificação
                        <input
                            type="number"
                            value={String(config.CONCURRENCY_LIMIT || "")}
                            onChange={(e) => set("CONCURRENCY_LIMIT", e.target.value)}
                        />
                    </label>
                    <label>
                        Timeout de requisição
                        <input
                            type="number"
                            value={String(config.REQUEST_TIMEOUT || "")}
                            onChange={(e) => set("REQUEST_TIMEOUT", e.target.value)}
                        />
                    </label>
                    <label>
                        Token da API externa
                        <input
                            value={String(config.API_TOKEN || "")}
                            onChange={(e) => set("API_TOKEN", e.target.value)}
                        />
                    </label>
                    <label>
                        User-Agent
                        <input
                            value={String(config.USER_AGENT || "")}
                            onChange={(e) => set("USER_AGENT", e.target.value)}
                        />
                    </label>
                    <label>Saúde automática (segundos)<input type="number" min="15" value={String(config.HEALTH_CHECK_INTERVAL_SECONDS || "")} onChange={(e) => set("HEALTH_CHECK_INTERVAL_SECONDS", e.target.value)} /></label>
                    <label>Atualização automática do xTeVe<select value={String(config.AUTO_UPDATE_XTEVE || "0")} onChange={(e) => set("AUTO_UPDATE_XTEVE", e.target.value)}><option value="0">Desativada</option><option value="1">Ativada</option></select></label>
                    <label>Número de tuners<input type="number" min="1" value={String(config.NUMBER_OF_TUNERS || "")} onChange={(e) => set("NUMBER_OF_TUNERS", e.target.value)} /></label>
                    <label>Fonte EPG<select value={String(config.EPG_SOURCE || "XEPG")} onChange={(e) => set("EPG_SOURCE", e.target.value)}><option value="PMS">PMS</option><option value="XEPG">XEPG</option></select></label>
                    <label>Interface API<select value={String(config.API_INTERFACE_ENABLED || "1")} onChange={(e) => set("API_INTERFACE_ENABLED", e.target.value)}><option value="1">Ativada</option><option value="0">Desativada</option></select></label>
                    <label>Agenda de arquivos<input value={String(config.FILE_UPDATE_SCHEDULE || "")} onChange={(e) => set("FILE_UPDATE_SCHEDULE", e.target.value)} placeholder="0800,1200,1800" /></label>
                    <label>Atualizar arquivos ao iniciar<select value={String(config.UPDATE_FILES_ON_STARTUP || "0")} onChange={(e) => set("UPDATE_FILES_ON_STARTUP", e.target.value)}><option value="0">Não</option><option value="1">Sim</option></select></label>
                    <label>Local de arquivos temporários<input value={String(config.TEMP_FILES_LOCATION || "")} onChange={(e) => set("TEMP_FILES_LOCATION", e.target.value)} /></label>
                    <label>Cache de imagens XMLTV<select value={String(config.IMAGE_CACHING || "1")} onChange={(e) => set("IMAGE_CACHING", e.target.value)}><option value="1">Ativado</option><option value="0">Desativado</option></select></label>
                    <label>Substituir imagens ausentes<select value={String(config.REPLACE_MISSING_PROGRAM_IMAGES || "1")} onChange={(e) => set("REPLACE_MISSING_PROGRAM_IMAGES", e.target.value)}><option value="1">Ativado</option><option value="0">Desativado</option></select></label>
                    <label>Buffer de stream<select value={String(config.STREAM_BUFFER_ENABLED || "0")} onChange={(e) => set("STREAM_BUFFER_ENABLED", e.target.value)}><option value="0">Desativado</option><option value="1">Ativado</option></select></label>
                    <label>Endereço UDPxy<input value={String(config.UDPPROXY_ADDRESS || "")} onChange={(e) => set("UDPPROXY_ADDRESS", e.target.value)} /></label>
                    <label>Tamanho do buffer (MB)<input type="number" min="1" value={String(config.BUFFER_SIZE_MB || "")} onChange={(e) => set("BUFFER_SIZE_MB", e.target.value)} /></label>
                    <label>Timeout de cliente (ms)<input type="number" min="1" value={String(config.CLIENT_CONNECTION_TIMEOUT_MS || "")} onChange={(e) => set("CLIENT_CONNECTION_TIMEOUT_MS", e.target.value)} /></label>
                    <label>Caminho do FFmpeg<input value={String(config.FFMPEG_BINARY_PATH || "")} onChange={(e) => set("FFMPEG_BINARY_PATH", e.target.value)} /></label>
                    <label>Opções do FFmpeg<input value={String(config.FFMPEG_OPTIONS || "")} onChange={(e) => set("FFMPEG_OPTIONS", e.target.value)} /></label>
                    <label>Caminho do VLC/CVLC<input value={String(config.VLC_BINARY_PATH || "")} onChange={(e) => set("VLC_BINARY_PATH", e.target.value)} /></label>
                    <label>Opções do VLC/CVLC<input value={String(config.VLC_OPTIONS || "")} onChange={(e) => set("VLC_OPTIONS", e.target.value)} /></label>
                    <label>Local dos backups<input value={String(config.BACKUP_LOCATION || "")} onChange={(e) => set("BACKUP_LOCATION", e.target.value)} /></label>
                    <label>Backups mantidos<input type="number" min="1" value={String(config.BACKUPS_TO_KEEP || "")} onChange={(e) => set("BACKUPS_TO_KEEP", e.target.value)} /></label>
                    <label>Autenticação web<select value={String(config.WEB_AUTHENTICATION || "1")} onChange={(e) => set("WEB_AUTHENTICATION", e.target.value)}><option value="1">Ativada</option><option value="0">Desativada</option></select></label>
                </div>
                <label>
                    Links remotos M3U, separados por ;
                    <textarea
                        value={String(config.REMOTE_M3U_URLS || "")}
                        onChange={(e) => set("REMOTE_M3U_URLS", e.target.value)}
                    />
                </label>
                <label>
                    Links EPG XMLTV, separados por ;
                    <textarea
                        value={String(config.EPG_URLS || "")}
                        onChange={(e) => set("EPG_URLS", e.target.value)}
                    />
                </label>
                <button className="button primary" onClick={save}>
                    <Save size={15} />{" "}
                    {saved ? "Configurações salvas" : "Salvar configurações"}
                </button>
            </div>
        </>
    );
}
function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [form, setForm] = useState({
        username: "",
        password: "",
        role: "viewer",
    });
    const [editing, setEditing] = useState<User | null>(null);
    const load = () => {
        api<User[]>("/api/v1/users")
            .then(setUsers)
            .catch(() => undefined);
    };
    useEffect(() => {
        load();
    }, []);
    const create = (e: React.FormEvent) => {
        e.preventDefault();
        send("/api/v1/users", form)
            .then(() => {
                setForm({ username: "", password: "", role: "viewer" });
                load();
            })
            .catch(() => alert("Não foi possível criar o usuário."));
    };
    const update = () =>
        editing &&
        api(`/api/v1/users/${editing.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: form.username, role: editing.role, password: form.password }),
        }).then(() => {
            setEditing(null);
            setForm({ ...form, password: "" });
            load();
        });
    return (
        <>
            <Header
                kicker="CONTROLE DE ACESSO"
                title="Usuários"
                description="Gerencie contas, papéis e senhas do sistema."
            />
            <div className="panel">
                <PanelTitle kicker="NOVO ACESSO" title="Adicionar usuário" />
                <form className="user-form" onSubmit={create}>
                    <input
                        placeholder="Nome de usuário"
                        required
                        value={form.username}
                        onChange={(e) => setForm({ ...form, username: e.target.value })}
                    />
                    <input
                        type="password"
                        placeholder="Senha"
                        required
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                    />
                    <select
                        value={form.role}
                        onChange={(e) => setForm({ ...form, role: e.target.value })}
                    >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                        <option value="admin">Admin</option>
                    </select>
                    <button className="button primary">
                        <UserRound size={15} /> Criar usuário
                    </button>
                </form>
                <div className="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Usuário</th>
                                <th>Papel</th>
                                <th>Criação</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((u) => (
                                <tr key={u.id}>
                                    <td>{u.id}</td>
                                    <td>
                                        <b>{u.username}</b>
                                    </td>
                                    <td>
                                        <span className="tag">{u.role}</span>
                                    </td>
                                    <td>{u.created_at || "-"}</td>
                                    <td>
                                        <button
                                            className="text-button"
                                            onClick={() => {
                                                setEditing(u);
                                                setForm({ ...form, username: u.username, password: "" });
                                            }}
                                        >
                                            Editar
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            {editing && (
                <Modal
                    title={`Editar ${editing.username}`}
                    close={() => setEditing(null)}
                >
                    <label>
                        Nome de usuário
                        <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
                    </label>
                    <label>
                        Papel
                        <select
                            value={editing.role}
                            onChange={(e) =>
                                setEditing({ ...editing, role: e.target.value as User["role"] })
                            }
                        >
                            <option value="viewer">Viewer</option>
                            <option value="editor">Editor</option>
                            <option value="admin">Admin</option>
                        </select>
                    </label>
                    <label>
                        Nova senha (opcional)
                        <input
                            type="password"
                            value={form.password}
                            onChange={(e) => setForm({ ...form, password: e.target.value })}
                        />
                    </label>
                    <button className="button primary" onClick={update}>
                        <Save size={15} /> Salvar
                    </button>
                </Modal>
            )}
        </>
    );
}
function Player() {
    const [channel, setChannel] = useState<Channel | null>(null);
    useEffect(() => {
        const f = (e: Event) => setChannel((e as CustomEvent<Channel>).detail);
        addEventListener("play-channel", f);
        return () => removeEventListener("play-channel", f);
    }, []);
    useEffect(() => {
        if (!channel) return;
        const video = document.getElementById("video") as HTMLVideoElement;
        let hls: Hls | null = null;
        if (channel.url.includes(".m3u8") && Hls.isSupported()) {
            hls = new Hls({ enableWorker: true, lowLatencyMode: true });
            hls.loadSource(channel.url);
            hls.attachMedia(video);
        } else video.src = channel.url;
        return () => {
            hls?.destroy();
            video.pause();
            video.src = "";
        };
    }, [channel]);
    return channel ? (
        <Modal
            title={`Visualizando: ${channel.name}`}
            close={() => setChannel(null)}
        >
            <video id="video" className="video" controls autoPlay />
        </Modal>
    ) : null;
}
function App() {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        api<{ user: User }>("/api/me")
            .then((d) => setUser(d.user))
            .catch(() => undefined)
            .finally(() => setLoading(false));
    }, []);
    if (loading)
        return (
            <div className="loading">
                <CircleGauge size={23} /> Carregando operação...
            </div>
        );
    if (!user) return <Login />;
    const path = window.location.pathname;
    let content: React.ReactNode = <Dashboard user={user} />;
    if (path === "/channels") content = <Channels user={user} />;
    if (path === "/playlists") content = <Playlists />;
    if (path === "/settings") content = <SettingsPage />;
    if (path === "/users") content = <UsersPage />;
    return (
        <Shell user={user}>
            {content}
            <Player />
        </Shell>
    );
}
createRoot(document.getElementById("root")!).render(<App />);
