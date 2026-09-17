import { useEffect, useState } from "react";
import { Bell, CheckCircle2, Info, TriangleAlert, X, XCircle } from "lucide-react";
import { api } from "../services/api";

type Notice = { level: "success" | "info" | "warning" | "error"; title: string; message: string; timestamp: string };
const icon = { success: CheckCircle2, info: Info, warning: TriangleAlert, error: XCircle };

export function Notifications() {
    const [items, setItems] = useState<Notice[]>([]);
    const [paused, setPaused] = useState<Record<string, boolean>>({});
    const [visible, setVisible] = useState<Record<string, boolean>>({});
    useEffect(() => {
        const load = () => api<Notice[]>("/api/v1/notifications").then((next) => {
            setItems(next);
            setVisible((old) => { const copy = { ...old }; next.forEach((_, i) => { if (copy[String(i)] === undefined) copy[String(i)] = true; }); return copy; });
        }).catch(() => undefined);
        load(); const timer = window.setInterval(load, 3000); return () => window.clearInterval(timer);
    }, []);
    return <aside className="notification-rail" aria-label="Notificações">
        <div className="notification-head"><span><Bell size={16} /> Avisos</span><strong>{items.length}</strong></div>
        {items.slice(0, 8).map((item, index) => {
            const key = `${item.timestamp}-${item.message}`; const Icon = icon[item.level] || Info;
            if (visible[String(index)] === false) return null;
            return <article key={key} className={`notification ${item.level}`} onMouseEnter={() => setPaused((p) => ({ ...p, [key]: true }))} onMouseLeave={() => setPaused((p) => ({ ...p, [key]: false }))}>
                <Icon size={18} /><div><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.timestamp).toLocaleTimeString()}</small></div>
                <button aria-label="Fechar" onClick={() => setVisible((v) => ({ ...v, [String(index)]: false }))}><X size={14} /></button>
                <span className={`notification-timer ${paused[key] ? "paused" : ""}`} />
            </article>;
        })}
    </aside>;
}
