import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { CalendarDays, Check, FileUp, Pencil, Plus, RefreshCw, Save, Search, Trash2, Tv, Upload, X } from "lucide-react";
import { api } from "../../services/api";
import type { Channel, EpgSource, User } from "../../types";
import { Empty, Header, Modal, PanelTitle, hasPermission } from "../../components/Common";

type Tab = "sources" | "channels" | "programmes";
type GuideForm = { id?: number; name: string; url: string };
type Programme = { id: number; channel_id: number; channel_name: string; title: string; description: string; category: string; start_at: string; end_at: string; recurrence: "once" | "daily" | "weekly"; weekdays: number[]; season: string; episode: string; rating: string; image: string };
type ProgrammeForm = Omit<Programme, "id" | "channel_name">;
type ChannelForm = { name: string; channel_number: string; tvg_id: string; url: string; logo: string; group_title: string; country: string; state: string; city: string; category: string; source: string; epgId: string };
type ChannelColumn = "channel_number" | "name" | "tvg_id" | "epg_source" | "epg_id" | "status" | "category" | "group_title" | "country" | "state" | "city" | "actions";

const WEEKDAYS = [[0, "Seg"], [1, "Ter"], [2, "Qua"], [3, "Qui"], [4, "Sex"], [5, "Sáb"], [6, "Dom"]] as const;
const columnNames: Record<ChannelColumn, string> = { channel_number: "CH. NO.", name: "Canal", tvg_id: "TVG ID", epg_source: "Guia XMLTV", epg_id: "ID XMLTV", status: "Status", category: "Categoria", group_title: "Grupo", country: "País", state: "Estado", city: "Cidade", actions: "Ações" };
const defaultColumns: ChannelColumn[] = ["channel_number", "name", "tvg_id", "epg_source", "epg_id", "status", "category", "actions"];
const localDateTime = (date: Date) => { const offset = date.getTimezoneOffset() * 60000; return new Date(date.getTime() - offset).toISOString().slice(0, 16); };
const emptyProgramme = (channelId: number): ProgrammeForm => { const start = new Date(); start.setMinutes(0, 0, 0); start.setHours(start.getHours() + 1); const end = new Date(start.getTime() + 60 * 60000); return { channel_id: channelId, title: "", description: "", category: "", start_at: localDateTime(start), end_at: localDateTime(end), recurrence: "once", weekdays: [], season: "", episode: "", rating: "", image: "" }; };
const programmeForm = (programme: Programme): ProgrammeForm => ({ channel_id: programme.channel_id, title: programme.title, description: programme.description || "", category: programme.category || "", start_at: programme.start_at.slice(0, 16), end_at: programme.end_at.slice(0, 16), recurrence: programme.recurrence, weekdays: programme.weekdays || [], season: programme.season || "", episode: programme.episode || "", rating: programme.rating || "", image: programme.image || "" });

export function EpgGuidesPage({ user }: { user: User }) {
    const [tab, setTab] = useState<Tab>("sources");
    const [sources, setSources] = useState<EpgSource[]>([]);
    const [guideSearch, setGuideSearch] = useState("");
    const [channels, setChannels] = useState<Channel[]>([]);
    const [programmes, setProgrammes] = useState<Programme[]>([]);
    const [message, setMessage] = useState("");
    const [busy, setBusy] = useState(false);
    const [guideForm, setGuideForm] = useState<GuideForm | null>(null);
    const [guideFile, setGuideFile] = useState<File | null>(null);
    const [channelForm, setChannelForm] = useState<ChannelForm | null>(null);
    const [editingChannelId, setEditingChannelId] = useState<number | null>(null);
    const [programmeFormState, setProgrammeFormState] = useState<ProgrammeForm | null>(null);
    const [editingProgramme, setEditingProgramme] = useState<number | null>(null);
    const [channelSearch, setChannelSearch] = useState("");
    const [channelStatus, setChannelStatus] = useState("todos");
    const [channelCategory, setChannelCategory] = useState("todos");
    const [channelCountry, setChannelCountry] = useState("todos");
    const [channelState, setChannelState] = useState("todos");
    const [channelCity, setChannelCity] = useState("todos");
    const [channelSort, setChannelSort] = useState<ChannelColumn>("channel_number");
    const [sortDesc, setSortDesc] = useState(false);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(30);
    const [selected, setSelected] = useState<number[]>([]);
    const [bulkSource, setBulkSource] = useState("");
    const [columns, setColumns] = useState<ChannelColumn[]>(() => { try { return JSON.parse(localStorage.getItem("epg-channel-columns") || "null") || defaultColumns; } catch { return defaultColumns; } });
    const [columnsOpen, setColumnsOpen] = useState(false);
    const [programmeChannel, setProgrammeChannel] = useState("");
    const [programmeSearch, setProgrammeSearch] = useState("");

    const canViewEpg = hasPermission(user, "epg", "view");
    const canCreate = hasPermission(user, "epg", "create");
    const canEdit = hasPermission(user, "epg", "edit");
    const canDelete = hasPermission(user, "epg", "delete");
    const canSync = hasPermission(user, "epg", "execute");
    const canCreateChannels = hasPermission(user, "channels", "create");
    const canEditChannels = hasPermission(user, "channels", "edit") || (editingChannelId === -1 && canCreateChannels);
    const canDeleteChannels = hasPermission(user, "channels", "delete");

    const loadSources = async () => { try { setSources(await api<EpgSource[]>("/api/v1/epg/sources")); } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível carregar as fontes XMLTV."); } };
    const loadChannels = async () => { try { setChannels(await api<Channel[]>(`/api/v1/epg/channels?search=${encodeURIComponent(channelSearch)}`)); } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível carregar os canais."); } };
    const loadProgrammes = async () => { const query = programmeChannel ? `?channel_id=${programmeChannel}` : ""; try { setProgrammes(await api<Programme[]>(`/api/v1/epg/programmes${query}`)); } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível carregar a programação."); } };
    const refresh = () => Promise.all([loadSources(), loadChannels(), loadProgrammes()]);

    useEffect(() => { refresh(); }, []);
    useEffect(() => { const timer = setTimeout(loadChannels, 250); return () => clearTimeout(timer); }, [channelSearch]);
    useEffect(() => { loadProgrammes(); }, [programmeChannel]);
    useEffect(() => { localStorage.setItem("epg-channel-columns", JSON.stringify(columns)); }, [columns]);

    const saveGuide = async (event: FormEvent) => {
        event.preventDefault();
        if (!guideForm) return;
        setBusy(true);
        try {
            const body = guideFile ? new FormData() : JSON.stringify({ name: guideForm.name.trim(), url: guideForm.url.trim() });
            if (body instanceof FormData) {
                body.append("name", guideForm.name.trim());
                body.append("url", guideForm.url.trim());
                body.append("file", guideFile as File);
            }
            const url = guideForm.id ? `/api/v1/epg/sources/${guideForm.id}` : "/api/v1/epg/sources";
            await api(url, { method: guideForm.id ? "PUT" : "POST", headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" }, body });
            setGuideForm(null); setGuideFile(null); setMessage("Guia XMLTV validada e salva."); await loadSources();
        } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível salvar a guia."); }
        finally { setBusy(false); }
    };

    const syncGuide = async (source: EpgSource) => {
        setBusy(true);
        try { await api(`/api/v1/epg/sources/${source.id}/sync`, { method: "POST" }); setMessage(`Guia '${source.name}' sincronizada.`); await loadSources(); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Falha ao sincronizar a guia."); }
        finally { setBusy(false); }
    };

    const deleteGuide = async (source: EpgSource) => {
        if (!confirm(`Remover a guia '${source.name}'? Os vínculos dos canais serão limpos.`)) return;
        try { await api(`/api/v1/epg/sources/${source.id}`, { method: "DELETE" }); setMessage("Guia removida."); await Promise.all([loadSources(), loadChannels()]); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível remover a guia."); }
    };

    const openChannel = (channel: Channel) => { setEditingChannelId(channel.id); setChannelForm({ name: channel.name, channel_number: String(channel.channel_number ?? ""), tvg_id: channel.tvg_id || "", url: channel.url || "", logo: channel.logo || "", group_title: channel.group_title || "", country: channel.country || "", state: channel.state || "", city: channel.city || "", category: channel.category || "tv", source: String(channel.epg_source_id || ""), epgId: channel.epg_channel_id || channel.tvg_id || "" }); };
    const saveChannel = async (channelId: number) => {
        if (!channelForm) return;
        try {
            if (channelId <= 0 || editingChannelId === null) {
                await api<Channel>("/api/v1/channels", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: channelForm.name, channel_number: channelForm.channel_number, tvg_id: channelForm.tvg_id, url: channelForm.url, logo: channelForm.logo, group_title: channelForm.group_title, country: channelForm.country, state: channelForm.state, city: channelForm.city, category: channelForm.category, ...(canEdit && channelForm.source ? { epg_source_id: channelForm.source, epg_channel_id: channelForm.epgId } : {}) }) });
            } else {
                if (canEditChannels) await api(`/api/v1/epg/channels/${channelId}/details`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: channelForm.name, channel_number: channelForm.channel_number, tvg_id: channelForm.tvg_id, url: channelForm.url, logo: channelForm.logo, group_title: channelForm.group_title, country: channelForm.country, state: channelForm.state, city: channelForm.city, category: channelForm.category }) });
                if (canEdit) await api(`/api/v1/epg/channels/${channelId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ epg_source_id: channelForm.source, epg_channel_id: channelForm.source ? channelForm.epgId : "" }) });
            }
            setChannelForm(null); setEditingChannelId(null); setMessage("Canal e associação XMLTV atualizados."); await loadChannels();
        } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível salvar o canal."); }
    };

    const deleteChannel = async (channel: Channel) => {
        if (!confirm(`Excluir o canal '${channel.name}' do banco?`)) return;
        try { await api(`/api/v1/channels/${channel.id}`, { method: "DELETE" }); setSelected(current => current.filter(id => id !== channel.id)); setMessage(`Canal '${channel.name}' removido.`); await loadChannels(); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível excluir o canal."); }
    };

    const deleteSelectedChannels = async () => {
        if (!selected.length || !confirm(`Excluir ${selected.length} canal(is) selecionado(s)? Esta ação não pode ser desfeita.`)) return;
        try { await Promise.all(selected.map(channelId => api(`/api/v1/channels/${channelId}`, { method: "DELETE" }))); setMessage(`${selected.length} canal(is) removido(s).`); setSelected([]); await loadChannels(); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível excluir todos os canais selecionados."); await loadChannels(); }
    };

    const saveBulk = async () => {
        if (!bulkSource || !selected.length) return;
        try { await Promise.all(selected.map(channelId => api(`/api/v1/epg/channels/${channelId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ epg_source_id: bulkSource === "none" ? null : bulkSource, epg_channel_id: bulkSource === "none" ? "" : channels.find(channel => channel.id === channelId)?.tvg_id || "" }) }))); setMessage(`${selected.length} canal(is) atualizado(s).`); setSelected([]); await loadChannels(); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Falha na associação em lote."); }
    };

    const saveProgramme = async (event: FormEvent) => {
        event.preventDefault();
        if (!programmeFormState) return;
        try {
            const url = editingProgramme ? `/api/v1/epg/programmes/${editingProgramme}` : "/api/v1/epg/programmes";
            await api(url, { method: editingProgramme ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(programmeFormState) });
            setProgrammeFormState(null); setEditingProgramme(null); setMessage("Programação salva."); await loadProgrammes();
        } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível salvar a programação."); }
    };

    const deleteProgramme = async (programme: Programme) => {
        if (!confirm(`Excluir '${programme.title}'?`)) return;
        try { await api(`/api/v1/epg/programmes/${programme.id}`, { method: "DELETE" }); setMessage("Programação removida."); await loadProgrammes(); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível remover a programação."); }
    };

    const filteredChannels = channels.filter(channel => (channelStatus === "todos" || channel.status === channelStatus) && (channelCategory === "todos" || channel.category === channelCategory) && (channelCountry === "todos" || channel.country === channelCountry) && (channelState === "todos" || channel.state === channelState) && (channelCity === "todos" || channel.city === channelCity));
    const orderedChannels = filteredChannels.slice().sort((a, b) => { const left = channelSort === "epg_source" ? a.epg_source_name : channelSort === "epg_id" ? a.epg_channel_id : a[channelSort as keyof Channel]; const right = channelSort === "epg_source" ? b.epg_source_name : channelSort === "epg_id" ? b.epg_channel_id : b[channelSort as keyof Channel]; const result = String(left ?? "").localeCompare(String(right ?? ""), "pt-BR", { numeric: true, sensitivity: "base" }); return sortDesc ? -result : result; });
    const pageCount = Math.max(1, Math.ceil(orderedChannels.length / pageSize));
    const pageChannels = orderedChannels.slice((page - 1) * pageSize, page * pageSize);
    const visibleSelected = pageChannels.length > 0 && pageChannels.every(channel => selected.includes(channel.id));
    const filteredProgrammes = programmes.filter(programme => `${programme.title} ${programme.channel_name} ${programme.category}`.toLowerCase().includes(programmeSearch.toLowerCase())).sort((a, b) => a.start_at.localeCompare(b.start_at));
    const filteredSources = sources.filter(source => `${source.name} ${source.source_url} ${source.last_error}`.toLowerCase().includes(guideSearch.toLowerCase()));
    const toggleColumn = (column: ChannelColumn) => setColumns(current => current.includes(column) ? current.filter(item => item !== column) : [...current, column]);
    const renderChannelCell = (channel: Channel, column: ChannelColumn) => {
        switch (column) {
            case "channel_number": return channel.channel_number ?? channel.id;
            case "name": return channel.name;
            case "tvg_id": return channel.tvg_id || "-";
            case "epg_source": return channel.epg_source_name || "-";
            case "epg_id": return channel.epg_channel_id || "-";
            case "status": return channel.status;
            case "category": return channel.category;
            case "group_title": return channel.group_title || "-";
            case "country": return channel.country || "-";
            case "state": return channel.state || "-";
            case "city": return channel.city || "-";
            case "actions": return <div className="epg-actions">{(canEditChannels || canEdit) && <button className="icon-button" title="Editar canal e vínculo XMLTV" onClick={() => openChannel(channel)}><Pencil size={15} /></button>}{canDeleteChannels && <button className="icon-button" title="Excluir canal" onClick={() => deleteChannel(channel)}><Trash2 size={15} /></button>}</div>;
        }
    };

    return <>
        <Header kicker="PROGRAMAÇÃO" title="Guias EPG / XMLTV" description="Administre fontes XMLTV, canais vinculados e grades de programação." >
            <button className="button subtle" onClick={refresh}><RefreshCw size={15} /> Atualizar</button>
            {tab === "sources" && canCreate && <button className="button primary" onClick={() => { setGuideFile(null); setGuideForm({ name: "", url: "" }); }}><Plus size={15} /> Nova guia</button>}
            {tab === "channels" && canCreateChannels && <button className="button primary" onClick={() => { setEditingChannelId(-1); setChannelForm({ name: "", channel_number: "", tvg_id: "", url: "", logo: "", group_title: "", country: "Outros", state: "Nacional/Geral", city: "Geral", category: "tv", source: "", epgId: "" }); }}><Plus size={15} /> Adicionar canal</button>}
            {tab === "programmes" && canCreate && <button className="button primary" disabled={!channels.length} onClick={() => { const selectedChannel = Number(programmeChannel || channels[0]?.id); if (selectedChannel) { setProgrammeChannel(String(selectedChannel)); setEditingProgramme(null); setProgrammeFormState(emptyProgramme(selectedChannel)); } }}><Plus size={15} /> Novo programa</button>}
        </Header>
        <div className="epg-tabs" role="tablist" aria-label="Administração EPG">
            <button role="tab" aria-selected={tab === "sources"} className={tab === "sources" ? "active" : ""} onClick={() => setTab("sources")}><Upload size={15} /> Guias</button>
            <button role="tab" aria-selected={tab === "channels"} className={tab === "channels" ? "active" : ""} onClick={() => setTab("channels")}><Tv size={15} /> Canais</button>
            <button role="tab" aria-selected={tab === "programmes"} className={tab === "programmes" ? "active" : ""} onClick={() => setTab("programmes")}><CalendarDays size={15} /> Programação</button>
        </div>
        {message && <div className="epg-message" role="status">{message}<button className="icon-button" title="Fechar mensagem" onClick={() => setMessage("")}><X size={14} /></button></div>}

        {tab === "sources" && <section className="panel table-panel">
            <PanelTitle kicker="FONTES XMLTV" title="Guias cadastradas" badge={`${sources.length} guia(s)`} />
            <div className="toolbar"><div className="search"><Search size={16} /><input value={guideSearch} onChange={event => setGuideSearch(event.target.value)} placeholder="Buscar guia por nome, URL ou erro" /></div></div>
            <div className="table-scroll"><table><thead><tr><th>Nome</th><th>Origem</th><th>Canais XMLTV</th><th>Canais vinculados</th><th>Sincronização</th><th>Ações</th></tr></thead>
                <tbody>{filteredSources.map(source => <tr key={source.id}><td><b>{source.name}</b></td><td className="epg-source-url">{source.source_url || "Arquivo importado"}</td><td>{source.channel_count}</td><td>{source.assigned_channels}</td><td>{source.synced_at || "Nunca"}{source.last_error && <small className="epg-error">{source.last_error}</small>}</td><td className="epg-actions">{canSync && source.source_url && <button className="icon-button" title="Sincronizar agora" disabled={busy} onClick={() => syncGuide(source)}><RefreshCw size={15} /></button>}{canEdit && <button className="icon-button" title="Editar guia ou substituir arquivo" onClick={() => { setGuideFile(null); setGuideForm({ id: source.id, name: source.name, url: source.source_url }); }}><Pencil size={15} /></button>}{canDelete && <button className="icon-button" title="Excluir guia" onClick={() => deleteGuide(source)}><Trash2 size={15} /></button>}</td></tr>)}</tbody>
            </table></div>{!filteredSources.length && <Empty text={sources.length ? "Nenhuma guia corresponde à pesquisa." : "Nenhuma guia cadastrada. Crie uma guia por URL ou importe XML/XML.GZ."} />}
        </section>}

        {tab === "channels" && <section className="panel table-panel epg-channel-panel">
            <PanelTitle kicker="ADMINISTRAÇÃO DE CANAIS" title="Canais e vínculos XMLTV" badge={`${orderedChannels.length} canal(is)`} />
            <div className="toolbar"><div className="search"><Search size={16} /><input value={channelSearch} onChange={event => { setChannelSearch(event.target.value); setPage(1); }} placeholder="Buscar por nome, TVG ID, URL ou local" /></div>
                <select value={channelStatus} onChange={event => { setChannelStatus(event.target.value); setPage(1); }}><option value="todos">Todos os status</option><option value="online">Online</option><option value="offline">Offline</option><option value="desconhecido">Não verificado</option></select>
                <select value={channelCategory} onChange={event => { setChannelCategory(event.target.value); setPage(1); }}><option value="todos">Todas as categorias</option>{[...new Set(channels.map(channel => channel.category))].sort().map(category => <option key={category} value={category}>{category}</option>)}</select>
                <select value={channelCountry} onChange={event => { setChannelCountry(event.target.value); setPage(1); }}><option value="todos">Todos os países</option>{[...new Set(channels.map(channel => channel.country).filter(Boolean))].sort().map(country => <option key={country} value={country}>{country}</option>)}</select>
                <select value={channelState} onChange={event => { setChannelState(event.target.value); setPage(1); }}><option value="todos">Todos os estados</option>{[...new Set(channels.map(channel => channel.state).filter(Boolean))].sort().map(state => <option key={state} value={state}>{state}</option>)}</select>
                <select value={channelCity} onChange={event => { setChannelCity(event.target.value); setPage(1); }}><option value="todos">Todas as cidades</option>{[...new Set(channels.map(channel => channel.city).filter(Boolean))].sort().map(city => <option key={city} value={city}>{city}</option>)}</select>
                <div className="column-picker"><button className="button subtle" onClick={() => setColumnsOpen(open => !open)}>Colunas</button>{columnsOpen && <div className="column-picker-menu">{(Object.keys(columnNames) as ChannelColumn[]).map(column => <label key={column}><input type="checkbox" checked={columns.includes(column)} onChange={() => toggleColumn(column)} />{columnNames[column]}</label>)}</div>}</div>
            </div>
            {(canEdit || canDeleteChannels) && <div className="editor-actions"><label><input type="checkbox" checked={visibleSelected} onChange={event => setSelected(current => event.target.checked ? [...new Set([...current, ...pageChannels.map(channel => channel.id)])] : current.filter(id => !pageChannels.some(channel => channel.id === id)))} /> Selecionar página</label><span>{selected.length} selecionado(s)</span>{canEdit && <><select value={bulkSource} onChange={event => setBulkSource(event.target.value)}><option value="">Vínculo em lote...</option><option value="none">Remover vínculo EPG</option>{sources.map(source => <option key={source.id} value={source.id}>{source.name}</option>)}</select><button className="button subtle" disabled={!selected.length || !bulkSource} onClick={saveBulk}><Check size={14} /> Aplicar vínculo</button></>}{canDeleteChannels && <button className="button danger" disabled={!selected.length} onClick={deleteSelectedChannels}><Trash2 size={14} /> Excluir selecionados</button>}</div>}
            <div className="editor-actions"><label>Ordenar por<select value={channelSort} onChange={event => setChannelSort(event.target.value as ChannelColumn)}>{(columns.filter(column => column !== "actions")).map(column => <option key={column} value={column}>{columnNames[column]}</option>)}</select></label><button className="button subtle" onClick={() => setSortDesc(value => !value)}>{sortDesc ? "Z → A" : "A → Z"}</button><label>Por página<input className="page-size" type="number" min="1" max="200" value={pageSize} onChange={event => setPageSize(Math.min(200, Math.max(1, Number(event.target.value) || 1)))} /></label><div className="pagination"><button className="icon-button" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>‹</button><span>Página {page} de {pageCount}</span><button className="icon-button" disabled={page >= pageCount} onClick={() => setPage(value => value + 1)}>›</button></div></div>
            <div className="table-scroll"><table><thead><tr><th><input type="checkbox" aria-label="Selecionar página" checked={visibleSelected} onChange={event => setSelected(current => event.target.checked ? [...new Set([...current, ...pageChannels.map(channel => channel.id)])] : current.filter(id => !pageChannels.some(channel => channel.id === id)))} /></th>{columns.map(column => <th key={column}><button className="table-sort" onClick={() => { setChannelSort(column); setSortDesc(current => channelSort === column ? !current : false); }}>{columnNames[column]}</button></th>)}</tr></thead>
                <tbody>{pageChannels.map(channel => <tr key={channel.id}><td><input type="checkbox" checked={selected.includes(channel.id)} onChange={event => setSelected(current => event.target.checked ? [...current, channel.id] : current.filter(id => id !== channel.id))} /></td>{columns.map(column => <td key={column} className={column === "name" ? "channel-name" : undefined}>{renderChannelCell(channel, column)}</td>)}</tr>)}</tbody>
            </table></div>{!pageChannels.length && <Empty text="Nenhum canal corresponde aos filtros." />}
        </section>}

        {tab === "programmes" && <section className="panel table-panel epg-programmes-panel">
            <PanelTitle kicker="GRADE DE PROGRAMAÇÃO" title="Programas por canal" badge={`${filteredProgrammes.length} programa(s)`} />
            <div className="toolbar"><select value={programmeChannel} onChange={event => setProgrammeChannel(event.target.value)}><option value="">Todos os canais</option>{channels.map(channel => <option key={channel.id} value={channel.id}>{channel.channel_number ? `${channel.channel_number} · ` : ""}{channel.name}</option>)}</select><div className="search"><Search size={16} /><input value={programmeSearch} onChange={event => setProgrammeSearch(event.target.value)} placeholder="Buscar programa, canal ou categoria" /></div></div>
            <div className="table-scroll"><table><thead><tr><th>Canal</th><th>Programa</th><th>Início</th><th>Fim</th><th>Recorrência</th><th>Categoria</th><th>Ações</th></tr></thead>
                <tbody>{filteredProgrammes.map(programme => <tr key={programme.id}><td>{programme.channel_name}</td><td><b>{programme.title}</b>{programme.description && <small className="epg-programme-description">{programme.description}</small>}</td><td>{programme.start_at.replace("T", " ")}</td><td>{programme.end_at.replace("T", " ")}</td><td>{programme.recurrence === "weekly" ? `Semanal (${programme.weekdays.map(day => WEEKDAYS[day]?.[1]).join(", ")})` : programme.recurrence === "daily" ? "Diária" : "Única"}</td><td>{programme.category || "-"}</td><td className="epg-actions">{canEdit && <button className="icon-button" title="Editar programa" onClick={() => { setEditingProgramme(programme.id); setProgrammeFormState(programmeForm(programme)); }}><Pencil size={15} /></button>}{canDelete && <button className="icon-button" title="Excluir programa" onClick={() => deleteProgramme(programme)}><Trash2 size={15} /></button>}</td></tr>)}</tbody>
            </table></div>{!filteredProgrammes.length && <Empty text="Nenhuma programação cadastrada para este filtro." />}
        </section>}

        {guideForm && <Modal title={guideForm.id ? "Editar guia XMLTV" : "Criar guia XMLTV"} close={() => { if (!busy) { setGuideForm(null); setGuideFile(null); } }}>
            <form className="edit-form" onSubmit={saveGuide}><label>Nome da guia<input required value={guideForm.name} onChange={event => setGuideForm({ ...guideForm, name: event.target.value })} /></label><label>URL da fonte XMLTV<input type="url" value={guideForm.url} disabled={Boolean(guideFile)} onChange={event => setGuideForm({ ...guideForm, url: event.target.value })} placeholder="https://servidor/guia.xml.gz" /></label><div className="epg-upload"><label><FileUp size={16} />{guideForm.id ? "Substituir arquivo XMLTV" : "Importar XML/XML.GZ"}<input type="file" accept=".xml,.gz,application/xml,application/gzip" onChange={event => { const file = event.target.files?.[0] || null; setGuideFile(file); if (file) setGuideForm(current => current ? { ...current, url: "" } : current); }} /></label>{guideFile && <button type="button" className="icon-button" title="Remover arquivo selecionado" onClick={() => setGuideFile(null)}><X size={15} /></button>}</div><p className="muted-text">A guia é validada antes de substituir o conteúdo ativo. XML compactado: até 50 MB.</p><div className="modal-actions"><button type="button" className="button subtle" disabled={busy} onClick={() => { setGuideForm(null); setGuideFile(null); }}>Cancelar</button><button className="button primary" disabled={busy || (!guideForm.id && !guideFile && !guideForm.url) || Boolean(guideFile && guideForm.url)}>{busy ? "Validando..." : <>{guideForm.id ? <Save size={15} /> : <Upload size={15} />}{guideForm.id ? " Salvar guia" : " Validar e criar"}</>}</button></div></form>
        </Modal>}

        {channelForm && <Modal title="Editar canal e associação EPG" close={() => { setChannelForm(null); setEditingChannelId(null); }}><div className="form-grid"><label>Nome do canal<input disabled={!canEditChannels} value={channelForm.name} onChange={event => setChannelForm({ ...channelForm, name: event.target.value })} /></label><label>CH. NO.<input type="number" min="0" value={channelForm.channel_number} disabled={!canEditChannels} onChange={event => setChannelForm({ ...channelForm, channel_number: event.target.value })} /></label><label>TVG ID<input disabled={!canEditChannels} value={channelForm.tvg_id} onChange={event => setChannelForm({ ...channelForm, tvg_id: event.target.value })} /></label><label>URL do canal<input type="url" disabled={!canEditChannels} value={channelForm.url} onChange={event => setChannelForm({ ...channelForm, url: event.target.value })} /></label><label>Logo<input disabled={!canEditChannels} value={channelForm.logo} onChange={event => setChannelForm({ ...channelForm, logo: event.target.value })} /></label><label>Grupo<input disabled={!canEditChannels} value={channelForm.group_title} onChange={event => setChannelForm({ ...channelForm, group_title: event.target.value })} /></label><label>País<input disabled={!canEditChannels} value={channelForm.country} onChange={event => setChannelForm({ ...channelForm, country: event.target.value })} /></label><label>Estado<input disabled={!canEditChannels} value={channelForm.state} onChange={event => setChannelForm({ ...channelForm, state: event.target.value })} /></label><label>Cidade<input disabled={!canEditChannels} value={channelForm.city} onChange={event => setChannelForm({ ...channelForm, city: event.target.value })} /></label><label>Categoria<select disabled={!canEditChannels} value={channelForm.category} onChange={event => setChannelForm({ ...channelForm, category: event.target.value })}>{["tv", "vod", "series", "radio", "outros"].map(value => <option key={value}>{value}</option>)}</select></label><label>Guia XMLTV<select disabled={!canEdit} value={channelForm.source} onChange={event => setChannelForm({ ...channelForm, source: event.target.value, epgId: event.target.value ? channelForm.epgId : "" })}><option value="">Sem guia</option>{sources.map(source => <option key={source.id} value={source.id}>{source.name}</option>)}</select></label><label>ID XMLTV do canal<input disabled={!canEdit || !channelForm.source} value={channelForm.epgId} onChange={event => setChannelForm({ ...channelForm, epgId: event.target.value })} placeholder={channelForm.tvg_id || "ID na guia"} /></label></div><div className="modal-actions"><button className="button subtle" onClick={() => { setChannelForm(null); setEditingChannelId(null); }}>Cancelar</button><button className="button primary" disabled={!canEdit && !canEditChannels} onClick={() => editingChannelId && saveChannel(editingChannelId)}>Salvar alterações</button></div></Modal>}

        {programmeFormState && <Modal title={editingProgramme ? "Editar programação" : "Criar programação"} close={() => { setProgrammeFormState(null); setEditingProgramme(null); }}><form className="edit-form" onSubmit={saveProgramme}><div className="form-grid"><label>Canal<select required disabled={Boolean(editingProgramme)} value={programmeFormState.channel_id} onChange={event => setProgrammeFormState({ ...programmeFormState, channel_id: Number(event.target.value) })}>{channels.map(channel => <option key={channel.id} value={channel.id}>{channel.name}</option>)}</select></label><label>Título do programa<input required value={programmeFormState.title} onChange={event => setProgrammeFormState({ ...programmeFormState, title: event.target.value })} /></label><label>Categoria<input value={programmeFormState.category} onChange={event => setProgrammeFormState({ ...programmeFormState, category: event.target.value })} /></label><label>Início<input type="datetime-local" required value={programmeFormState.start_at} onChange={event => setProgrammeFormState({ ...programmeFormState, start_at: event.target.value })} /></label><label>Fim<input type="datetime-local" required value={programmeFormState.end_at} onChange={event => setProgrammeFormState({ ...programmeFormState, end_at: event.target.value })} /></label><label>Recorrência<select value={programmeFormState.recurrence} onChange={event => setProgrammeFormState({ ...programmeFormState, recurrence: event.target.value as ProgrammeForm["recurrence"] })}><option value="once">Uma vez</option><option value="daily">Todos os dias</option><option value="weekly">Dias da semana</option></select></label>{programmeFormState.recurrence === "weekly" && <fieldset className="epg-weekdays"><legend>Repetir nos dias</legend>{WEEKDAYS.map(([day, label]) => <label key={day}><input type="checkbox" checked={programmeFormState.weekdays.includes(day)} onChange={event => setProgrammeFormState({ ...programmeFormState, weekdays: event.target.checked ? [...programmeFormState.weekdays, day].sort() : programmeFormState.weekdays.filter(value => value !== day) })} />{label}</label>)}</fieldset>}<label>Temporada<input value={programmeFormState.season} onChange={event => setProgrammeFormState({ ...programmeFormState, season: event.target.value })} /></label><label>Episódio<input value={programmeFormState.episode} onChange={event => setProgrammeFormState({ ...programmeFormState, episode: event.target.value })} /></label><label>Classificação indicativa<input value={programmeFormState.rating} onChange={event => setProgrammeFormState({ ...programmeFormState, rating: event.target.value })} /></label><label>Imagem/logo (URL)<input type="url" value={programmeFormState.image} onChange={event => setProgrammeFormState({ ...programmeFormState, image: event.target.value })} /></label></div><label>Descrição<textarea rows={4} value={programmeFormState.description} onChange={event => setProgrammeFormState({ ...programmeFormState, description: event.target.value })} /></label><div className="modal-actions"><button type="button" className="button subtle" onClick={() => { setProgrammeFormState(null); setEditingProgramme(null); }}>Cancelar</button><button className="button primary"><Save size={15} />Salvar programação</button></div></form></Modal>}
    </>;
}
