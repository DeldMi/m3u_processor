import { useEffect, useState } from "react";
import { Activity, Database, HardDrive, MemoryStick, RefreshCw, Save, Server, ShieldCheck } from "lucide-react";
import { api } from "../../services/api";
import { Header, PanelTitle, Metric } from "../../components/Common";

type Config = Record<string, string | number>;
type Resources = { current: Record<string, number>; history: Array<Record<string, number | string>> };

const bytes = (n: number) => n > 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(1)} GB` : `${(n / 1024 ** 2).toFixed(1)} MB`;

export function ResourceSettingsPage() {
    const [config, setConfig] = useState<Config>({});
    const [resources, setResources] = useState<Resources | null>(null);
    const [diagnostic, setDiagnostic] = useState<{ status: string; warnings: string[] } | null>(null);
    const [saved, setSaved] = useState(false);

    const load = () => {
        api<Config>("/api/config").then(setConfig).catch(() => undefined);
        api<Resources>("/api/v1/resources").then(setResources).catch(() => undefined);
        api<{ status: string; warnings: string[] }>("/api/v1/resources/diagnostics").then(setDiagnostic).catch(() => undefined);
    };
    useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);
    const set = (key: string, value: string | number) => setConfig((old) => ({ ...old, [key]: value }));
    const save = () => api("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) }).then(() => { setSaved(true); setTimeout(() => setSaved(false), 2500); });
    const current = resources?.current || {};

    return <>
        <Header kicker="SISTEMA / RECURSOS" title="Hardware e Software" description="Limites, runtime, armazenamento, memória, processamento e monitoramento do servidor." />
        <section className="resource-metric-grid">
            <Metric label="CPU" value={`${current.cpu_percent ?? 0}%`} detail={`${current.process_cpu_percent ?? 0}% processo`} tone="blue" />
            <Metric label="RAM" value={`${current.ram_percent ?? 0}%`} detail={bytes(current.process_rss_bytes ?? 0) + " processo"} tone="green" />
            <Metric label="Disco" value={`${current.disk_percent ?? 0}%`} detail={bytes(current.disk_free_bytes ?? 0) + " livres"} tone="blue" />
            <Metric label="Threads" value={current.process_threads ?? 0} detail="processo atual" tone="blue" />
        </section>

        <div className="settings-resource-grid">
            <section className="panel"><PanelTitle kicker="MEMÓRIA" title="Limites e comportamento" /><div className="form-grid">
                <label>Alerta de RAM (%)<input type="number" min="1" max="99" value={String(config.RAM_ALERT_PERCENT ?? 70)} onChange={e => set("RAM_ALERT_PERCENT", e.target.value)} /></label>
                <label>Crítico de RAM (%)<input type="number" min="1" max="100" value={String(config.RAM_CRITICAL_PERCENT ?? 85)} onChange={e => set("RAM_CRITICAL_PERCENT", e.target.value)} /></label>
                <label>Histórico de métricas<input type="number" min="30" max="1000" value={String(config.RESOURCE_HISTORY_SIZE ?? 120)} onChange={e => set("RESOURCE_HISTORY_SIZE", e.target.value)} /></label>
                <label>Cache de imagens<select value={String(config.IMAGE_CACHING ?? "1")} onChange={e => set("IMAGE_CACHING", e.target.value)}><option value="1">Ativado</option><option value="0">Desativado</option></select></label>
            </div></section>

            <section className="panel"><PanelTitle kicker="ARMAZENAMENTO" title="Disco e temporários" /><div className="form-grid">
                <label>Alerta de disco (%)<input type="number" min="1" max="99" value={String(config.DISK_ALERT_PERCENT ?? 80)} onChange={e => set("DISK_ALERT_PERCENT", e.target.value)} /></label>
                <label>Crítico de disco (%)<input type="number" min="1" max="100" value={String(config.DISK_CRITICAL_PERCENT ?? 90)} onChange={e => set("DISK_CRITICAL_PERCENT", e.target.value)} /></label>
                <label>Diretório temporário<input value={String(config.TEMP_FILES_LOCATION ?? "")} onChange={e => set("TEMP_FILES_LOCATION", e.target.value)} placeholder="Padrão do sistema" /></label>
                <label>Backups mantidos<input type="number" min="1" value={String(config.BACKUPS_TO_KEEP ?? 5)} onChange={e => set("BACKUPS_TO_KEEP", e.target.value)} /></label>
            </div></section>

            <section className="panel"><PanelTitle kicker="PROCESSAMENTO" title="M3U, rede e concorrência" /><div className="form-grid">
                <label>Workers/concorrência<input type="number" min="1" value={String(config.CONCURRENCY_LIMIT ?? 50)} onChange={e => set("CONCURRENCY_LIMIT", e.target.value)} /></label>
                <label>Timeout HTTP (s)<input type="number" min="1" value={String(config.REQUEST_TIMEOUT ?? 6)} onChange={e => set("REQUEST_TIMEOUT", e.target.value)} /></label>
                <label>Máximo de canais por lista<input type="number" min="1" value={String(config.MAX_CHANNELS_PER_FILE ?? 400)} onChange={e => set("MAX_CHANNELS_PER_FILE", e.target.value)} /></label>
                <label>User-Agent<input value={String(config.USER_AGENT ?? "")} onChange={e => set("USER_AGENT", e.target.value)} /></label>
            </div></section>

            <section className="panel"><PanelTitle kicker="PUBLICAÇÃO" title="Comportamento padrão da sincronização" /><div className="form-grid"><label>Publicação padrão<select value={String(config.SYNC_PUBLICATION_MODE ?? "NONE")} onChange={e => set("SYNC_PUBLICATION_MODE", e.target.value)}><option value="NONE">Não criar nem atualizar</option><option value="CREATE">Criar somente novos</option><option value="UPDATE">Atualizar existentes</option><option value="CREATE_UPDATE">Criar + atualizar</option></select></label></div><p className="muted">O padrão é seguro: uma auditoria não publica links sem uma escolha explícita.</p></section>
        </div>

        <section className="panel"><PanelTitle kicker="DIAGNÓSTICO" title="Estado do runtime" badge={diagnostic?.status === "warning" ? "ATENÇÃO" : "OK"} /><div className="diagnostic-grid"><div><Server size={18}/><strong>Python</strong><span>{current.python || "—"}</span></div><div><Activity size={18}/><strong>CPU</strong><span>{current.cpu_count || "—"} threads lógicas</span></div><div><MemoryStick size={18}/><strong>Memória do processo</strong><span>{bytes(current.process_rss_bytes || 0)}</span></div><div><HardDrive size={18}/><strong>Armazenamento</strong><span>{current.disk_percent ?? 0}% utilizado</span></div><div><Database size={18}/><strong>Coleta GC</strong><span>{current.gc_counts ? String(current.gc_counts) : "automática"}</span></div><div><ShieldCheck size={18}/><strong>Diagnóstico</strong><span>{diagnostic?.warnings?.length ? diagnostic.warnings.join(" ") : "Nenhuma anomalia detectada no período observado."}</span></div></div></section>

        <div className="actions"><button className="button subtle" onClick={load}><RefreshCw size={15}/> Atualizar métricas</button><button className="button primary" onClick={save}><Save size={15}/> {saved ? "Configurações salvas" : "Salvar recursos"}</button></div>
    </>;
}
