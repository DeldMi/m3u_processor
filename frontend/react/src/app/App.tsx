import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../services/api";
import type { User } from "../types";
import { hasPermission, Shell, Login } from "../components/Common";
import { Dashboard } from "../features/dashboard/DashboardPage";
import { Channels } from "../features/channels/ChannelsPage";
import { Playlists } from "../features/playlists/PlaylistsPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { UsersPage } from "../features/users/UsersPage";
import { Player } from "../features/player/Player";
import { Notifications } from "../components/Notifications";

const ROUTES = {
    "/": ["dashboard", "view"],
    "/channels": ["channels", "view"],
    "/playlists": ["playlists", "view"],
    "/settings": ["settings", "view"],
    "/users": ["users", "view"],
} as const;

function Forbidden({ path }: { path: string }) {
    return <section className="panel"><span className="kicker">ACESSO RESTRITO</span><h1>Acesso não autorizado</h1><p className="muted">Sua conta não possui permissão para abrir <b>{path}</b>. Volte ao Painel geral ou solicite acesso ao administrador.</p><a className="button primary" href="/">Voltar ao painel</a></section>;
}

export function App() {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    useEffect(() => { api<{ user: User }>("/api/me").then((d) => setUser(d.user)).catch(() => undefined).finally(() => setLoading(false)); }, []);
    if (loading) return <div className="loading">Carregando operação...</div>;
    if (!user) return <Login />;

    const path = window.location.pathname;
    const route = ROUTES[path as keyof typeof ROUTES];
    if (route && !hasPermission(user, route[0], route[1])) {
        return <Shell user={user}><Forbidden path={path} /><Player /></Shell>;
    }

    let content: ReactNode = <Dashboard user={user} />;
    if (path === "/channels") content = <Channels user={user} />;
    if (path === "/playlists") content = <Playlists user={user} />;
    if (path === "/settings") content = <SettingsPage />;
    if (path === "/users") content = <UsersPage user={user} />;
    return <Shell user={user}>{content}<Player /><Notifications /></Shell>;
}