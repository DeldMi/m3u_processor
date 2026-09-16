import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../services/api";
import type { User } from "../types";
import { Shell, Login } from "../components/Common";
import { Dashboard } from "../features/dashboard/DashboardPage";
import { Channels } from "../features/channels/ChannelsPage";
import { Playlists } from "../features/playlists/PlaylistsPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { UsersPage } from "../features/users/UsersPage";
import { Player } from "../features/player/Player";

export function App() {
 const [user,setUser]=useState<User|null>(null);
 const [loading,setLoading]=useState(true);
 useEffect(()=>{api<{user:User}>("/api/me").then(d=>setUser(d.user)).catch(()=>undefined).finally(()=>setLoading(false));},[]);
 if(loading) return <div className="loading">Carregando operação...</div>;
 if(!user) return <Login/>;
 const path=window.location.pathname;
 let content: ReactNode=<Dashboard user={user}/>;
 if(path==="/channels") content=<Channels user={user}/>;
 if(path==="/playlists") content=<Playlists/>;
 if(path==="/settings") content=<SettingsPage/>;
 if(path==="/users") content=<UsersPage/>;
 return <Shell user={user}>{content}<Player/></Shell>;
}
