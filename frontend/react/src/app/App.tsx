import {useEffect,useState} from "react";
import type {ReactNode} from "react";
import {api} from "../services/api";
import type {User} from "../types";
import {hasPermission,Shell,Login} from "../components/Common";
import {ThemeProvider} from "../components/ThemeProvider";
import {Dashboard} from "../features/dashboard/DashboardPage";
// A página completa de Canais preserva filtros, seleção, colunas,
// ordenação, edição, ações operacionais e criação de playlists.
import {Channels} from "../features/channels/ChannelsPage";
import {Playlists} from "../features/playlists/PlaylistsPage";
import {SettingsHubPage} from "../features/settings/SettingsHubPage";
import {ResourceSettingsPage} from "../features/settings/ResourceSettingsPage";
import {ThemeSettingsPage} from "../features/settings/ThemeSettingsPage";
import {UsersPage} from "../features/users/UsersPage";
import {Player} from "../features/player/Player";

const ROUTES={
    "/":["dashboard","view"],
    "/channels":["channels","view"],
    "/playlists":["playlists","view"],
    "/settings":["settings","view"],
    "/settings/resources":["settings","view"],
    "/settings/themes":["settings","view"],
    "/users":["users","view"],
} as const;

function Forbidden({path}:{path:string}){return <section className="panel"><span className="kicker">ACESSO RESTRITO</span><h1>Acesso não autorizado</h1><p className="muted">Sua conta não possui permissão para abrir <b>{path}</b>.</p><a className="button primary" href="/">Voltar ao painel</a></section>}

export function App(){
    const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true);
    useEffect(()=>{api<{user:User}>("/api/me").then(d=>setUser(d.user)).catch(()=>undefined).finally(()=>setLoading(false))},[]);
    if(loading)return <div className="loading">Carregando operação...</div>;
    if(!user)return <ThemeProvider userKey="login"><Login/></ThemeProvider>;
    const rawPath=window.location.pathname;
    const path=rawPath.startsWith("/app-assets") ? (rawPath.slice("/app-assets".length)||"/") : rawPath;
    const route=ROUTES[path as keyof typeof ROUTES];
    if(route&&!hasPermission(user,route[0],route[1]))return <ThemeProvider userKey={user.username}><Shell user={user}><Forbidden path={path}/><Player/></Shell></ThemeProvider>;
    let content:ReactNode=<Dashboard user={user}/>;
    if(path==="/channels")content=<Channels user={user}/>;
    if(path==="/playlists")content=<Playlists user={user}/>;
    if(path==="/settings")content=<SettingsHubPage/>;
    if(path==="/settings/resources")content=<ResourceSettingsPage/>;
    if(path==="/settings/themes")content=<ThemeSettingsPage user={user}/>;
    if(path==="/users")content=<UsersPage user={user}/>;
    return <ThemeProvider userKey={user.username}><Shell user={user}>{content}<Player/></Shell></ThemeProvider>
}
