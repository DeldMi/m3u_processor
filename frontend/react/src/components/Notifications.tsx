import { useEffect, useRef, useState } from "react";
import { Bell, CheckCircle2, Info, TriangleAlert, X, XCircle } from "lucide-react";
import { api } from "../services/api";

type Notice = { level: "success" | "info" | "warning" | "error"; title: string; message: string; timestamp: string };
const icon = { success: CheckCircle2, info: Info, warning: TriangleAlert, error: XCircle };
const DEFAULT_TTL = 7000;

export function Notifications() {
    const [items, setItems] = useState<Notice[]>([]);
    const [hidden, setHidden] = useState<Record<string, boolean>>({});
    const [paused, setPaused] = useState<Record<string, boolean>>({});
    const timers = useRef<Record<string, number>>({});

    useEffect(() => {
        const load = () => api<Notice[]>("/api/v1/notifications").then(setItems).catch(() => undefined);
        load();
        const poll = window.setInterval(load, 3000);
        return () => { window.clearInterval(poll); Object.values(timers.current).forEach(window.clearTimeout); };
    }, []);

    useEffect(() => {
        items.slice(0, 8).forEach((item) => {
            const key = `${item.timestamp}-${item.message}`;
            if (hidden[key] || timers.current[key]) return;
            timers.current[key] = window.setTimeout(() => setHidden((old) => ({ ...old, [key]: true })), DEFAULT_TTL);
        });
    }, [items, hidden]);

    const pause = (key: string) => setPaused((old) => ({ ...old, [key]: true }));
    const resume = (key: string) => setPaused((old) => ({ ...old, [key]: false }));

    return <aside className="notification-rail" aria-label="Notificações">
        <div className="notification-head"><span><Bell size={16} /> Avisos</span><strong>{items.filter((x) => !hidden[`${x.timestamp}-${x.message}`]).length}</strong></div>
        {items.slice(0, 8).map((item) => {
            const key = `${item.timestamp}-${item.message}`;
            const Icon = icon[item.level] || Info;
            if (hidden[key]) return null;
            return <article key={key} className={`notification ${item.level}`} onMouseEnter={() => pause(key)} onMouseLeave={() => resume(key)}>
                <Icon size={18} />
                <div><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.timestamp).toLocaleTimeString()}</small></div>
                <button aria-label="Fechar" onClick={() => setHidden((old) => ({ ...old, [key]: true }))}><X size={14} /></button>
                <span className={`notification-timer ${paused[key] ? "paused" : ""}`} />
            </article>;
        })}
    </aside>;
}