import React, { useEffect, useState } from "react";
import { Boxes, ChevronLeft, ChevronRight, ListVideo, Play, Plus, RefreshCw, Save, SlidersHorizontal, Trash2, Upload, Wifi, X } from "lucide-react";
import { api, send } from "../../services/api";
import type { Channel, ChannelColumn, ChannelOptions, EpgSource, Manifest, User } from "../../types";
import { Header, PanelTitle, Empty, Modal, canEdit, hasPermission } from "../../components/Common";


export function Channels({ user }: { user: User }) {
    const [channels, setChannels] = useState<Channel[]>([]);
    const [query, setQuery] = useState({
        search: "",
        country: "todos",
        state: "todos",
        city: "todos",
        category: "todos",
        status: "todos",
        sort: "channel_number",
        direction: "asc",
    });
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(50);
    const [selected, setSelected] = useState<number[]>([]);
    const [editing, setEditing] = useState<Channel | null>(null);
    const [builder, setBuilder] = useState(false);
    const [options, setOptions] = useState<ChannelOptions>({ country: [], state: [], city: [], category: [], status: [] });
    const [columnsOpen, setColumnsOpen] = useState(false);
    const [columns, setColumns] = useState<ChannelColumn[]>(() => {
        try { return JSON.parse(localStorage.getItem("channel-columns") || "null") || ["status", "id", "logo", "name", "country", "city", "group_title", "tvg_id", "latency_ms", "actions"]; } catch { return ["status", "id", "logo", "name", "country", "city", "group_title", "tvg_id", "latency_ms", "actions"]; }
    });
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
        query.state,
        query.city,
        query.category,
        query.status,
        query.sort,
        query.direction,
    ]);
    useEffect(() => { api<ChannelOptions>("/api/v1/channels/options").then(setOptions).catch(() => undefined); }, [channels]);
    useEffect(() => { localStorage.setItem("channel-columns", JSON.stringify(columns)); }, [columns]);
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
    const removeChannel = (channel: Channel) => {
        if (!confirm(`Excluir o canal '${channel.name}'?`)) return;
        api(`/api/v1/channels/${channel.id}`, { method: "DELETE" })
            .then(load)
            .catch(() => alert("Não foi possível excluir o canal."));
    };
    const updateQuery = (key: keyof typeof query, value: string) =>
        setQuery({ ...query, [key]: value });
    const sortBy = (field: string) => setQuery({ ...query, sort: field, direction: query.sort === field && query.direction === "asc" ? "desc" : "asc" });
    const toggleColumn = (column: ChannelColumn) => setColumns(columns.includes(column) ? columns.filter((item) => item !== column) : [...columns, column]);
    const columnLabels: Record<ChannelColumn, string> = { status: "Status", id: "Ch. No.", logo: "Logo", name: "Channel Name", country: "País", state: "Estado", city: "Cidade", playlist: "Playlist", group_title: "Group Title", epg_source: "Guia EPG", xmltv_file: "XMLTV File", tvg_id: "XMLTV ID", latency_ms: "Latência", auto_remove: "Remover OFF", actions: "Ações" };
    const header = (column: ChannelColumn) => <button className="table-sort" onClick={() => sortBy(column)}>{columnLabels[column]} {query.sort === column ? (query.direction === "asc" ? "↑" : "↓") : "↕"}</button>;
    const renderCell = (column: ChannelColumn, channel: Channel) => {
        switch (column) {
            case "status": return <button aria-label={`Status ${channel.name}: ${channel.status}`} className={`status-dot ${channel.status}`} disabled={!canEdit(user)} onClick={() => patch(`/api/v1/channels/${channel.id}/status`, { status: channel.status === "online" ? "offline" : "online" })} />;
            case "id": return channel.channel_number ?? channel.id;
            case "logo": return <span className="channel-logo">{channel.logo ? <img src={channel.logo} onError={event => { event.currentTarget.style.display = "none"; }} /> : <Wifi size={14} />}</span>;
            case "name": return <b>{channel.name}</b>;
            case "country": return channel.country || "-";
            case "state": return channel.state || "-";
            case "city": return channel.city || "-";
            case "playlist": return channel.playlist || "-";
            case "group_title": return channel.group_title || "-";
            case "epg_source": return channel.epg_source_name || "-";
            case "xmltv_file": return channel.xmltv_file || "-";
            case "tvg_id": return (channel.epg_source_id ? channel.epg_channel_id : "") || channel.tvg_id || "-";
            case "latency_ms": return `${channel.latency_ms || 0} ms`;
            case "auto_remove": return <input aria-label={`Remover ${channel.name} se offline`} type="checkbox" checked={Boolean(channel.auto_remove_if_offline)} disabled={!canEdit(user)} onChange={event => patch(`/api/v1/channels/${channel.id}/autoremove`, { auto_remove_if_offline: event.target.checked ? 1 : 0 })} />;
            case "actions": return <>{canEdit(user) && <button className="text-button" onClick={() => setEditing(channel)}>Editar</button>}{hasPermission(user, "channels", "delete") && <button className="icon-button" title="Excluir canal" onClick={() => removeChannel(channel)}><Trash2 size={14} /></button>}<button className="icon-button" title="Assistir" onClick={() => dispatchEvent(new CustomEvent("play-channel", { detail: channel }))}><Play size={14} /></button></>;
        }
    };
    return (
        <>
            <Header
                kicker="CATÁLOGO"
                title="Canais e editor"
                description="Filtre, audite e ajuste os metadados da sua grade."
            >
                {hasPermission(user, "channels", "create") && <button className="button primary" onClick={() => setEditing({ id: 0, name: "", url: "", category: "tv", status: "desconhecido", country: "Outros", state: "Nacional/Geral", city: "Geral", auto_remove_if_offline: 1 })}><Plus size={15} /> Adicionar canal</button>}
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
                    <select value={query.country} onChange={(e) => updateQuery("country", e.target.value)}><option value="todos">Todos os países</option>{options.country.map((value) => <option key={value}>{value}</option>)}</select>
                    <select value={query.state} onChange={(e) => updateQuery("state", e.target.value)}><option value="todos">Todos os estados</option>{options.state.map((value) => <option key={value}>{value}</option>)}</select>
                    <select value={query.city} onChange={(e) => updateQuery("city" as keyof typeof query, e.target.value)}><option value="todos">Todas as cidades</option>{options.city.map((value) => <option key={value}>{value}</option>)}</select>
                    <select
                        value={query.category}
                        onChange={(e) => updateQuery("category", e.target.value)}
                    >
                        <option value="todos">Todas as categorias</option>
                        {options.category.map((value) => <option key={value}>{value}</option>)}
                    </select>
                    <select
                        value={query.status}
                        onChange={(e) => updateQuery("status", e.target.value)}
                    >
                        <option value="todos">Todos os status</option>
                        {options.status.map((value) => <option key={value} value={value}>{value === "online" ? "Apenas online" : value === "offline" ? "Apenas offline" : value}</option>)}
                    </select>
                    <div className="column-picker"><button className="button subtle" onClick={() => setColumnsOpen(!columnsOpen)}>Colunas</button>{columnsOpen && <div className="column-picker-menu">{(Object.keys(columnLabels) as ChannelColumn[]).map((column) => <label key={column}><input type="checkbox" checked={columns.includes(column)} onChange={() => toggleColumn(column)} /> {columnLabels[column]}</label>)}</div>}</div>
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
                        disabled={!selected.length || !hasPermission(user, "playlists", "create")}
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
                                {columns.map((column) => <th key={column}>{column === "actions" ? columnLabels[column] : header(column)}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {visible.map((c) => (
                                <tr key={c.id}>
                                    <td><input type="checkbox" checked={selected.includes(c.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, c.id] : selected.filter((id) => id !== c.id))} /></td>
                                    {columns.map(column => <td key={column} className={column === "name" ? "channel-name" : undefined}>{renderCell(column, c)}</td>)}
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
                    user={user}
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

export function ChannelEditor({
    channel,
    user,
    close,
    saved,
}: {
    channel: Channel;
    user: User;
    close: () => void;
    saved: () => void;
}) {
    const [form, setForm] = useState(channel);
    const [epgSources, setEpgSources] = useState<EpgSource[]>([]);
    const [uploading, setUploading] = useState(false);
    useEffect(() => { if (hasPermission(user, "epg", "view")) api<EpgSource[]>("/api/v1/epg/sources").then(setEpgSources).catch(() => setEpgSources([])); }, [user]);
    const set = (key: keyof Channel, value: string | number) =>
        setForm({ ...form, [key]: value });
    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        const { epg_source_id, epg_channel_id, ...channelForm } = form;
        try {
            const result = await api<Channel>(channel.id ? `/api/v1/channels/${channel.id}` : "/api/v1/channels", {
                method: channel.id ? "PATCH" : "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(channelForm),
            });
            if (hasPermission(user, "epg", "edit")) {
                await api(`/api/v1/epg/channels/${channel.id || result.id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ epg_source_id: epg_source_id || "", epg_channel_id: epg_channel_id || "" }),
                });
            }
            saved();
        } catch {
            alert(channel.id ? "Não foi possível salvar o canal ou sua associação EPG." : "Não foi possível criar o canal ou sua associação EPG.");
        }
    };
    const uploadLogo = (file: File) => {
        const body = new FormData();
        body.append("image", file);
        setUploading(true);
        fetch("/api/v1/channels/logo", { method: "POST", body })
            .then((response) => { if (!response.ok) throw new Error("upload"); return response.json() as Promise<{ url: string }>; })
            .then((result) => set("logo", result.url))
            .catch(() => alert("Não foi possível enviar a imagem."))
            .finally(() => setUploading(false));
    };
    return (
        <Modal title={channel.id ? "Editar canal completo" : "Adicionar canal"} close={close}>
            <form className="edit-form" onSubmit={submit}>
                <div className="form-grid">
                    {(
                        [
                            "name",
                            "url",
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
                    <label>CH. NO.
                        <input
                            type="number"
                            min="0"
                            step="1"
                            value={form.channel_number ?? ""}
                            onChange={(e) => set("channel_number", e.target.value === "" ? "" : Number(e.target.value))}
                            placeholder="Ex.: 10"
                        />
                    </label>
                    <label>Logo por URL<input value={String(form.logo || "")} onChange={(e) => set("logo", e.target.value)} placeholder="https://..." /></label>
                    <label>Enviar logo do computador<input type="file" accept="image/png,image/jpeg,image/webp,image/gif" disabled={uploading} onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0])} /></label>
                    {hasPermission(user, "epg", "view") && <><label>Guia EPG / XMLTV<select disabled={!hasPermission(user, "epg", "edit")} value={form.epg_source_id || ""} onChange={(e) => setForm({ ...form, epg_source_id: e.target.value ? Number(e.target.value) : null, epg_channel_id: e.target.value ? form.epg_channel_id || form.tvg_id || "" : "" })}><option value="">Sem guia associada</option>{epgSources.map(source => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label>
                        <label>ID do canal na guia<input value={form.epg_channel_id || ""} disabled={!hasPermission(user, "epg", "edit") || !form.epg_source_id} onChange={(e) => set("epg_channel_id", e.target.value)} placeholder={form.tvg_id || "tvg-id"} /></label></>}
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
                        <Save size={15} /> {channel.id ? "Salvar canal" : "Criar canal"}
                    </button>
                </div>
            </form>
        </Modal>
    );
}

export function PlaylistBuilder({ ids, close }: { ids: number[]; close: () => void }) {
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
