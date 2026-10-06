import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { FileUp, Pencil, Plus, RefreshCw, Save, Trash2, Tv, Upload, X } from "lucide-react";
import { api } from "../../services/api";
import type { Channel, EpgSource, User } from "../../types";
import { Empty, Header, Modal, PanelTitle, hasPermission } from "../../components/Common";

type GuideForm = { id?: number; name: string; url: string };

export function EpgGuidesPage({ user }: { user: User }) {
    const [sources, setSources] = useState<EpgSource[]>([]);
    const [channels, setChannels] = useState<Channel[]>([]);
    const [search, setSearch] = useState("");
    const [form, setForm] = useState<GuideForm | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState("");
    const [drafts, setDrafts] = useState<Record<number, { source: string; xmltvId: string }>>({});
    const canCreate = hasPermission(user, "epg", "create");
    const canEdit = hasPermission(user, "epg", "edit");
    const canDelete = hasPermission(user, "epg", "delete");
    const canSync = hasPermission(user, "epg", "execute");

    const loadSources = () => api<EpgSource[]>("/api/v1/epg/sources").then(setSources).catch(() => setMessage("Não foi possível carregar as guias XMLTV."));
    const loadChannels = () => api<Channel[]>(`/api/v1/epg/channels?search=${encodeURIComponent(search)}`).then(setChannels).catch(() => setMessage("Não foi possível carregar os canais."));
    useEffect(() => { loadSources(); }, []);
    useEffect(() => { const timer = setTimeout(loadChannels, 250); return () => clearTimeout(timer); }, [search]);

    const submitGuide = async (event: FormEvent) => {
        event.preventDefault();
        if (!form) return;
        setBusy(true);
        try {
            if (form.id) {
                await api(`/api/v1/epg/sources/${form.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: form.name, url: form.url }) });
            } else {
                const body = new FormData();
                body.append("name", form.name);
                if (file) body.append("file", file);
                else body.append("url", form.url);
                await api("/api/v1/epg/sources", { method: "POST", body });
            }
            setForm(null); setFile(null); setMessage("Guia salva e XMLTV validado."); await loadSources();
        } catch (error) {
            setMessage(error instanceof Error ? error.message : "Não foi possível salvar a guia.");
        } finally { setBusy(false); }
    };

    const syncGuide = async (source: EpgSource) => {
        setBusy(true);
        try { await api(`/api/v1/epg/sources/${source.id}/sync`, { method: "POST" }); setMessage(`Guia '${source.name}' sincronizada.`); await loadSources(); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Falha ao sincronizar a guia."); }
        finally { setBusy(false); }
    };

    const deleteGuide = async (source: EpgSource) => {
        if (!confirm(`Remover a guia '${source.name}'? Os canais vinculados ficarão sem fonte EPG.`)) return;
        try { await api(`/api/v1/epg/sources/${source.id}`, { method: "DELETE" }); setMessage("Guia removida."); await Promise.all([loadSources(), loadChannels()]); }
        catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível remover a guia."); }
    };

    const saveChannel = async (channel: Channel) => {
        const draft = drafts[channel.id] || { source: String(channel.epg_source_id || ""), xmltvId: channel.epg_channel_id || channel.tvg_id || "" };
        try {
            await api(`/api/v1/epg/channels/${channel.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ epg_source_id: draft.source, epg_channel_id: draft.xmltvId }) });
            setMessage(`Associação EPG de '${channel.name}' atualizada.`); await loadChannels();
        } catch (error) { setMessage(error instanceof Error ? error.message : "Não foi possível associar a guia."); }
    };

    const draftFor = (channel: Channel) => drafts[channel.id] || { source: String(channel.epg_source_id || ""), xmltvId: channel.epg_channel_id || channel.tvg_id || "" };

    return <>
        <Header kicker="PROGRAMAÇÃO" title="Guias EPG / XMLTV" description="Cadastre fontes XMLTV, sincronize arquivos e associe cada canal ao identificador correto.">
            {canCreate && <button className="button primary" onClick={() => { setFile(null); setForm({ name: "", url: "" }); }}><Plus size={15} /> Adicionar guia</button>}
            <button className="button subtle" onClick={() => { loadSources(); loadChannels(); }}><RefreshCw size={15} /> Atualizar</button>
        </Header>
        {message && <div className="editor-actions" role="status">{message}</div>}
        <section className="panel table-panel">
            <PanelTitle kicker="FONTES XMLTV" title="Guias cadastradas" badge={`${sources.length} guia(s)`} />
            <div className="table-scroll"><table><thead><tr><th>Nome</th><th>Origem</th><th>Canais XMLTV</th><th>Canais associados</th><th>Última sincronização</th><th>Ações</th></tr></thead>
                <tbody>{sources.map(source => <tr key={source.id}><td><b>{source.name}</b></td><td className="epg-source-url">{source.source_url || "Arquivo importado"}</td><td>{source.channel_count}</td><td>{source.assigned_channels}</td><td>{source.synced_at || "Nunca"}{source.last_error && <small className="epg-error">{source.last_error}</small>}</td><td className="epg-actions">{canSync && source.source_url && <button className="icon-button" title="Sincronizar agora" disabled={busy} onClick={() => syncGuide(source)}><RefreshCw size={15} /></button>}{canEdit && <button className="icon-button" title="Editar fonte" onClick={() => setForm({ id: source.id, name: source.name, url: source.source_url })}><Pencil size={15} /></button>}{canDelete && <button className="icon-button" title="Excluir guia" onClick={() => deleteGuide(source)}><Trash2 size={15} /></button>}</td></tr>)}</tbody>
            </table></div>
            {!sources.length && <Empty text="Nenhuma guia XMLTV cadastrada. Adicione uma URL ou importe um arquivo .xml/.gz." />}
        </section>
        <section className="panel table-panel epg-channel-panel">
            <PanelTitle kicker="VÍNCULO DE CANAIS" title="Associar canal à guia" badge={`${channels.length} canal(is)`} />
            <div className="toolbar"><div className="search"><Tv size={16} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Pesquisar canal por nome, TVG ID ou local" /></div></div>
            <div className="table-scroll"><table><thead><tr><th>Canal</th><th>TVG ID</th><th>Guia XMLTV</th><th>ID na guia</th><th>Ação</th></tr></thead>
                <tbody>{channels.map(channel => { const draft = draftFor(channel); return <tr key={channel.id}><td><b>{channel.name}</b></td><td>{channel.tvg_id || "-"}</td><td><select disabled={!canEdit} value={draft.source} onChange={event => setDrafts(current => ({ ...current, [channel.id]: { ...draft, source: event.target.value, xmltvId: event.target.value ? draft.xmltvId : "" } }))}><option value="">Sem guia associada</option>{sources.map(source => <option key={source.id} value={source.id}>{source.name}</option>)}</select></td><td><input disabled={!canEdit || !draft.source} value={draft.xmltvId} onChange={event => setDrafts(current => ({ ...current, [channel.id]: { ...draft, xmltvId: event.target.value } }))} placeholder="Usa TVG ID se vazio" /></td><td>{canEdit && <button className="icon-button" title="Salvar associação" onClick={() => saveChannel(channel)}><Save size={15} /></button>}</td></tr>; })}</tbody>
            </table></div>
            {!channels.length && <Empty text="Nenhum canal encontrado." />}
        </section>
        {form && <Modal title={form.id ? "Editar guia XMLTV" : "Adicionar guia XMLTV"} close={() => { if (!busy) { setForm(null); setFile(null); } }}>
            <form className="edit-form" onSubmit={submitGuide}><label>Nome da guia<input required value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} placeholder="Ex.: Guia Nacional" /></label>
                {!form.id && <><label>URL XMLTV<input type="url" value={form.url} disabled={Boolean(file)} onChange={event => setForm({ ...form, url: event.target.value })} placeholder="https://exemplo/guia.xml.gz" /></label><div className="epg-upload"><label><FileUp size={16} /> Importar arquivo XML/XML.GZ<input type="file" accept=".xml,.gz,application/xml,application/gzip" onChange={event => { const selected = event.target.files?.[0] || null; setFile(selected); if (selected) setForm(current => current ? { ...current, url: "" } : current); }} /></label>{file && <button type="button" className="icon-button" title="Remover arquivo selecionado" onClick={() => setFile(null)}><X size={15} /></button>}</div><p className="muted-text">A fonte será validada como XMLTV antes de ser cadastrada. Limite: 50 MB compactados.</p></>}
                {form.id && <label>URL da fonte<input type="url" value={form.url} onChange={event => setForm({ ...form, url: event.target.value })} placeholder="Deixe vazio para uma guia importada" /></label>}
                <div className="modal-actions"><button type="button" className="button subtle" disabled={busy} onClick={() => { setForm(null); setFile(null); }}>Cancelar</button><button className="button primary" disabled={busy || (!form.id && !file && !form.url)}>{form.id ? <Save size={15} /> : <Upload size={15} />}{busy ? " Processando..." : form.id ? " Salvar guia" : " Validar e adicionar"}</button></div>
            </form>
        </Modal>}
    </>;
}