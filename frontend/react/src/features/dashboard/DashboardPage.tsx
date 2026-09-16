import React, { useEffect, useState } from "react";
import { Square, Zap } from "lucide-react";
import { api, send } from "../../services/api";
import type { InternetHealth, Status, User } from "../../types";
import { Header, PanelTitle, Empty, Metric, Legend, canEdit, hasPermission } from "../../components/Common";

export function Dashboard({ user }: { user: User }) {
    const [data, setData] = useState<Status | null>(null);
    const [internet, setInternet] = useState<InternetHealth | null>(null);
    const canViewLogs = hasPermission(user, "logs", "view");
    const canViewSync = hasPermission(user, "sync", "view");
    const load = () => api<Status>("/api/status").then(setData).catch(() => undefined);
    useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, []);
    useEffect(() => {
        const loadInternet = () => api<InternetHealth>("/api/v1/internet-health").then(setInternet).catch(() => setInternet(null));
        loadInternet(); const t = setInterval(loadInternet, 5000); return () => clearInterval(t);
    }, []);
    const total = data?.total_canais || 0;
    const online = data?.canais_online || 0;
    const offline = data?.canais_offline || 0;
    const unknown = data?.canais_desconhecidos || Math.max(total - online - offline, 0);
    const hasHealthResult = online + offline > 0;
    const rate = total && hasHealthResult ? Math.round((online / total) * 100) : null;
    const running = data?.status === "Executando..." || data?.status === "Pausado";
    const action = (url: string) => send(url).then(load);
    return <>
        <Header kicker="MONITORAMENTO AO VIVO" title="Painel geral" description="Visão operacional da auditoria, conectividade e geração das listas.">
            {canEdit(user) && <div className="actions"><button className="button primary" disabled={running} onClick={() => action("/api/v1/sync")}><Zap size={15} /> Iniciar sincronização</button><button className="button subtle" disabled={!running} onClick={() => action("/api/v1/sync/pause")}>{data?.status === "Pausado" ? "Retomar" : "Pausar"}</button><button className="button danger" disabled={!running} onClick={() => confirm("Interromper a execução atual?") && action("/api/v1/sync/stop")}><Square size={14} /> Interromper</button></div>}
        </Header>
        <section className="metric-grid"><Metric label="Status do processo" value={data?.status || "Carregando"} detail={canViewLogs ? (data?.ultimo_log || "Aguardando dados") : "estado operacional"} tone="blue" /><Metric label="Canais catalogados" value={total} detail="base atual" tone="blue" /><Metric label="Online" value={online} detail={rate === null ? "verificando" : `${rate}% da base`} tone="green" /><Metric label="Offline / removidos" value={offline} detail="última verificação" tone="red" /></section>
        <section className="panel internet-status-panel"><PanelTitle kicker="CONECTIVIDADE" title="Internet" badge="TESTE AUTOMÁTICO" /><div className="internet-status-content"><div className={`internet-status ${internet?.online ? "online" : internet ? "offline" : "unknown"}`}><i className="internet-status-dot" /><strong>{internet?.online ? "ONLINE" : internet ? "OFFLINE" : "VERIFICANDO"}</strong></div><div className="internet-ping"><span>Ping</span><b>{internet ? `${internet.latency_ms} ms` : "—"}</b></div><div className="internet-target"><span>Destino</span><b title={internet?.target || ""}>{internet?.target || "Carregando configuração..."}</b></div></div></section>
        <section className="split-grid"><div className="panel health-panel"><PanelTitle kicker="DISTRIBUIÇÃO" title="Saúde dos canais" badge="AO VIVO" /><div className="health-content"><div className="donut" style={{ "--progress": `${(rate || 0) * 3.6}deg` } as React.CSSProperties}><strong>{rate === null ? "..." : `${rate}%`}</strong><small>{rate === null ? "verificando" : "online"}</small></div><div className="legend"><Legend label="Online" value={online} color="green" /><Legend label="Offline" value={offline} color="red" /><Legend label="Não verificado" value={unknown} color="muted" /></div></div></div>
            {canViewLogs && <div className="panel"><PanelTitle kicker="ATIVIDADE" title="O que está acontecendo" badge={`${data?.log_count || 0} eventos`} /><div className="activity-list">{data?.logs?.slice(0, 12).map((l) => <div className={`activity ${l.level}`} key={`${l.timestamp}-${l.message}`}><time>{l.timestamp.slice(11)}</time><span>{l.message}</span></div>) || <Empty text="Nenhuma atividade registrada." />}</div></div>}
        </section>
        {canViewSync && <div className="panel"><PanelTitle kicker="PIPELINE" title="Progresso da operação" badge={data?.status || "Ocioso"} /><div className="progress-track"><span style={{ width: data?.status === "Concluido" ? "100%" : running ? "62%" : "12%" }} /></div><div className="progress-labels"><span>Leitura</span><span>Verificação</span><span>Particionamento</span><span>Concluído</span></div></div>}
    </>;
}