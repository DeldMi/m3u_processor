import { useEffect, useMemo, useRef, useState } from "react";
import { Bell, CheckCircle2, Info, TriangleAlert, X, XCircle, Trash2 } from "lucide-react";
import { api } from "../services/api";

type Notice = {
    id: string;
    level: "success" | "info" | "warning" | "error";
    title: string;
    message: string;
    timestamp: string;
    source?: string;
    path?: string;
    details?: string;
};

const icon = { success: CheckCircle2, info: Info, warning: TriangleAlert, error: XCircle };
const TOAST_TTL = 7000;
const STORAGE_SEEN = "m3u-notifications-seen-v2";
const STORAGE_CLEARED = "m3u-notifications-cleared-v2";

function readIds(key: string): Set<string> {
    try {
        const raw = JSON.parse(localStorage.getItem(key) || "[]");
        return new Set(Array.isArray(raw) ? raw.map(String).slice(-500) : []);
    } catch {
        return new Set();
    }
}

function saveIds(key: string, ids: Set<string>) {
    try { localStorage.setItem(key, JSON.stringify(Array.from(ids).slice(-500))); } catch { /* storage unavailable */ }
}

function noticeId(item: Partial<Notice>) {
    return String(item.id || `${item.timestamp || ""}|${item.level || "info"}|${item.title || ""}|${item.message || ""}`);
}

export function Notifications() {
    const [items, setItems] = useState<Notice[]>([]);
    const [open, setOpen] = useState(false);
    const [expanded, setExpanded] = useState<string | null>(null);
    const [toastIds, setToastIds] = useState<string[]>([]);
    const [paused, setPaused] = useState<Record<string, boolean>>({});
    const timers = useRef<Record<string, number>>({});
    const initialized = useRef(false);
    const seen = useRef<Set<string>>(readIds(STORAGE_SEEN));
    const cleared = useRef<Set<string>>(readIds(STORAGE_CLEARED));

    const dismissToast = (id: string) => {
        window.clearTimeout(timers.current[id]);
        delete timers.current[id];
        setToastIds((old) => old.filter((value) => value !== id));
    };

    const scheduleToast = (id: string) => {
        window.clearTimeout(timers.current[id]);
        timers.current[id] = window.setTimeout(() => dismissToast(id), TOAST_TTL);
    };

    const load = async () => {
        try {
            const response = await api<Notice[]>("/api/v1/notifications");
            const normalized = response.map((item) => ({ ...item, id: noticeId(item) }));
            setItems(normalized);

            const incoming = normalized.filter((item) => !seen.current.has(item.id) && !cleared.current.has(item.id));
            if (!initialized.current) {
                // O histórico existente nunca vira toast ao trocar/recarregar de página.
                normalized.forEach((item) => seen.current.add(item.id));
                saveIds(STORAGE_SEEN, seen.current);
                initialized.current = true;
            } else if (incoming.length) {
                incoming.forEach((item) => seen.current.add(item.id));
                saveIds(STORAGE_SEEN, seen.current);
                setToastIds((old) => Array.from(new Set([...incoming.map((item) => item.id), ...old])).slice(0, 6));
                incoming.slice(0, 6).forEach((item) => scheduleToast(item.id));
            }
        } catch {
            // Falhas de consulta não criam uma falsa notificação.
        }
    };

    useEffect(() => {
        void load();
        const poll = window.setInterval(() => void load(), 3000);
        return () => {
            window.clearInterval(poll);
            Object.values(timers.current).forEach(window.clearTimeout);
        };
    }, []);

    const visibleItems = useMemo(() => items.filter((item) => !cleared.current.has(item.id)), [items]);
    const unread = visibleItems.filter((item) => !seen.current.has(item.id)).length;
    const toastItems = toastIds.map((id) => items.find((item) => item.id === id)).filter(Boolean) as Notice[];

    const clearAll = () => {
        visibleItems.forEach((item) => cleared.current.add(item.id));
        saveIds(STORAGE_CLEARED, cleared.current);
        toastItems.forEach((item) => dismissToast(item.id));
        setExpanded(null);
        setItems((old) => old.filter((item) => !cleared.current.has(item.id)));
    };

    return <>
        <div className="notification-center" onMouseLeave={() => setOpen(false)}>
            <button className={`notification-bell ${open ? "active" : ""}`} onClick={() => setOpen((value) => !value)} title="Notificações" aria-label="Abrir notificações" aria-expanded={open}>
                <Bell size={18} />
                {visibleItems.length > 0 && <span className="notification-badge">{visibleItems.length > 99 ? "99+" : visibleItems.length}</span>}
            </button>
            {open && <section className="notification-panel" aria-label="Central de notificações">
                <div className="notification-panel-head">
                    <div><strong>Notificações</strong><small>{visibleItems.length ? `${visibleItems.length} registro(s)` : "Nenhuma notificação"}</small></div>
                    {visibleItems.length > 0 && <button className="notification-clear" onClick={clearAll} title="Limpar histórico"><Trash2 size={14} /> Limpar</button>}
                </div>
                <div className="notification-list">
                    {visibleItems.length === 0 && <div className="notification-empty"><Bell size={20} /><span>Nenhuma notificação registrada.</span></div>}
                    {visibleItems.map((item) => {
                        const Icon = icon[item.level] || Info;
                        const isExpanded = expanded === item.id;
                        return <article key={item.id} className={`notification-history ${item.level} ${isExpanded ? "expanded" : ""}`} onClick={() => setExpanded(isExpanded ? null : item.id)}>
                            <Icon size={17} />
                            <div className="notification-history-body">
                                <strong>{item.title}</strong>
                                <p>{item.message}</p>
                                <small>{new Date(item.timestamp).toLocaleString()} {item.source ? `• ${item.source}` : ""}</small>
                                {isExpanded && <div className="notification-details">
                                    <span><b>Quando:</b> {new Date(item.timestamp).toLocaleString()}</span>
                                    <span><b>Origem:</b> {item.source || "Execução do sistema"}</span>
                                    {item.path && <span><b>Local:</b> {item.path}</span>}
                                    {item.details && <span><b>Detalhes:</b> {item.details}</span>}
                                </div>}
                            </div>
                            <button className="notification-close" aria-label="Fechar aviso" onClick={(event) => { event.stopPropagation(); dismissToast(item.id); }}><X size={14} /></button>
                        </article>;
                    })}
                </div>
            </section>}
        </div>

        <div className="notification-toasts" aria-live="polite">
            {toastItems.map((item) => {
                const Icon = icon[item.level] || Info;
                return <article key={item.id} className={`notification-toast ${item.level}`} onMouseEnter={() => { window.clearTimeout(timers.current[item.id]); setPaused((old) => ({ ...old, [item.id]: true })); }} onMouseLeave={() => { setPaused((old) => ({ ...old, [item.id]: false })); scheduleToast(item.id); }}>
                    <Icon size={18} />
                    <div><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.timestamp).toLocaleTimeString()}</small></div>
                    <button aria-label="Fechar aviso" onClick={() => dismissToast(item.id)}><X size={14} /></button>
                    <span className={`notification-timer ${paused[item.id] ? "paused" : ""}`} />
                </article>;
            })}
        </div>
    </>;
}
