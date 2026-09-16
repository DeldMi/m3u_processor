import React, { useEffect, useState } from "react";
import { Copy, RefreshCw, Save, Settings } from "lucide-react";
import { api } from "../../services/api";
import type { Manifest, User } from "../../types";
import { Header, Empty, Modal, hasPermission } from "../../components/Common";

export function Playlists({ user }: { user: User }) {
    const canDelete = hasPermission(user, "playlists", "delete");
    const canEditSettings = hasPermission(user, "settings", "admin");
    const [items, setItems] = useState<Manifest[]>([]);
    const [status, setStatus] = useState("Aguardando");
    const [selected, setSelected] = useState<string[]>([]);
    const [editing, setEditing] = useState(false);
    const [baseUrl, setBaseUrl] = useState("");
    const [message, setMessage] = useState("");
    const load = () => api<{ status: string; manifestos: Manifest[] }>("/api/v1/playlists").then((d) => { setStatus(d.status); setItems(d.manifestos || []); setSelected([]); }).catch(() => undefined);
    useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, []);
    const all = items.length > 0 && selected.length === items.length;
    const remove = () => {
        if (!canDelete || !selected.length || !confirm(`Excluir ${selected.length} lista(s) e seus arquivos XML?`)) return;
        api("/api/v1/playlists", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ m3u_names: selected }) })
            .then(() => { setMessage("Listas excluídas."); load(); }).catch(() => setMessage("Não foi possível excluir as listas."));
    };
    const openEditor = () => {
        if (!canEditSettings) return;
        api<Record<string, string | number>>("/api/config").then((c) => { setBaseUrl(String(c.BASE_URL || "")); setEditing(true); }).catch(() => setMessage("Não foi possível carregar a configuração."));
    };
    const saveUrl = () => api("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ BASE_URL: baseUrl }) })
        .then(() => { setEditing(false); setMessage("Endereço público atualizado."); load(); }).catch(() => setMessage("Não foi possível salvar o endereço."));
    return <>
        <Header kicker="ENTREGA" title="Listas publicadas" description="Arquivos M3U e XMLTV criados pelo processamento atual.">
            <span className="live-status"><i /> {status}</span>
        </Header>
        <div className="panel table-panel">
            <div className="panel-title"><div><span className="kicker">ARQUIVOS PUBLICADOS</span><h2>Links disponíveis</h2></div><div className="actions">
                <button className="button subtle" onClick={load}><RefreshCw size={15} /> Atualizar</button>
                {canDelete && <button className="button subtle" disabled={!selected.length} onClick={remove}>Excluir selecionadas</button>}
                {canEditSettings && <button className="button primary" onClick={openEditor}><Settings size={15} /> Editar endereço</button>}
            </div></div>
            <div className="editor-actions"><label><input type="checkbox" checked={all} onChange={(e) => setSelected(e.target.checked ? items.map((i) => i.m3u_name) : [])} /> Selecionar todas</label><span className="muted-text">{selected.length} selecionada(s)</span>{message && <span className="muted-text">{message}</span>}</div>
            <div className="table-scroll"><table><thead><tr><th>Selecionar</th><th>Lista</th><th>Canais</th><th>M3U</th><th>EPG XMLTV</th><th>Atalhos</th></tr></thead><tbody>{items.map((i) => <tr key={i.m3u_name}>
                <td><input type="checkbox" checked={selected.includes(i.m3u_name)} onChange={(e) => setSelected(e.target.checked ? [...selected, i.m3u_name] : selected.filter((n) => n !== i.m3u_name))} /></td>
                <td><b>{i.m3u_name}</b></td><td>{i.total}</td>
                <td><a href={i.m3u_url} target="_blank" rel="noreferrer">{i.m3u_url}</a></td><td><a href={i.xml_url} target="_blank" rel="noreferrer">{i.xml_url}</a></td>
                <td><button className="icon-button" title="Copiar M3U" onClick={() => navigator.clipboard?.writeText(i.m3u_url)}><Copy size={15} /></button><button className="icon-button" title="Copiar XMLTV" onClick={() => navigator.clipboard?.writeText(i.xml_url)}><Copy size={15} /></button></td>
            </tr>)}</tbody></table></div>
            {!items.length && <Empty text="Nenhuma lista criada nesta sessão." />}
        </div>
        {editing && <Modal title="Editar endereço público das listas" close={() => setEditing(false)}><p className="muted-text">Esse endereço é usado pelos links M3U e XMLTV publicados.</p><label>URL base pública<input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://127.0.0.1:5000" /></label><div className="modal-actions"><button className="button subtle" onClick={() => setEditing(false)}>Cancelar</button><button className="button primary" onClick={saveUrl}><Save size={15} /> Salvar endereço</button></div></Modal>}
    </>;
}