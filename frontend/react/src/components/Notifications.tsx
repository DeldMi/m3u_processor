import { useEffect, useRef, useState } from "react";
import { Bell, CheckCircle2, Info, TriangleAlert, X, XCircle, Trash2 } from "lucide-react";
import { api } from "../services/api";

type Notice = { id:string; level:"success"|"info"|"warning"|"error"; title:string; message:string; timestamp:string; source?:string; path?:string; details?:string };
const icons = { success: CheckCircle2, info: Info, warning: TriangleAlert, error: XCircle };
const TTL = 7000;
const SEEN = "m3u-notifications-seen-v3";
const CLEARED = "m3u-notifications-cleared-v3";
const ids = (key:string) => { try { const v=JSON.parse(localStorage.getItem(key)||"[]"); return new Set(Array.isArray(v)?v.map(String).slice(-500):[]); } catch { return new Set<string>(); } };
const saveIds = (key:string,v:Set<string>) => { try { localStorage.setItem(key,JSON.stringify([...v].slice(-500))); } catch {} };
const nid = (n:Partial<Notice>) => String(n.id || `${n.timestamp||""}|${n.level||"info"}|${n.title||""}|${n.message||""}`);

export function Notifications(){
 const [items,setItems]=useState<Notice[]>([]),[open,setOpen]=useState(false),[expanded,setExpanded]=useState<string|null>(null),[toastIds,setToastIds]=useState<string[]>([]),[paused,setPaused]=useState<Record<string,boolean>>({});
 const timers=useRef<Record<string,number>>({}), closeTimer=useRef<number|undefined>(), initialized=useRef(false), seen=useRef(ids(SEEN)), cleared=useRef(ids(CLEARED));
 const dismiss=(id:string)=>{clearTimeout(timers.current[id]);delete timers.current[id];setToastIds(v=>v.filter(x=>x!==id));};
 const schedule=(id:string)=>{clearTimeout(timers.current[id]);timers.current[id]=window.setTimeout(()=>dismiss(id),TTL);};
 const load=async()=>{try{const response=await api<Notice[]>("/api/v1/notifications"), normalized=response.map(n=>({...n,id:nid(n)}));setItems(normalized);const incoming=normalized.filter(n=>!seen.current.has(n.id)&&!cleared.current.has(n.id));if(!initialized.current){normalized.forEach(n=>seen.current.add(n.id));saveIds(SEEN,seen.current);initialized.current=true;}else if(incoming.length){incoming.forEach(n=>seen.current.add(n.id));saveIds(SEEN,seen.current);setToastIds(v=>[...new Set([...incoming.map(n=>n.id),...v])].slice(0,6));incoming.slice(0,6).forEach(n=>schedule(n.id));}}catch{}};
 useEffect(()=>{void load();const poll=window.setInterval(()=>void load(),3000);return()=>{clearInterval(poll);Object.values(timers.current).forEach(clearTimeout);clearTimeout(closeTimer.current);};},[]);
 const visible=items.filter(n=>!cleared.current.has(n.id));
 const closeLater=()=>{clearTimeout(closeTimer.current);closeTimer.current=window.setTimeout(()=>setOpen(false),220);};
 const keepOpen=()=>clearTimeout(closeTimer.current);
 const clearAll=()=>{visible.forEach(n=>cleared.current.add(n.id));saveIds(CLEARED,cleared.current);toastIds.forEach(dismiss);setItems(v=>v.filter(n=>!cleared.current.has(n.id)));setExpanded(null);};
 const closeOne=(id:string)=>{cleared.current.add(id);saveIds(CLEARED,cleared.current);dismiss(id);setItems(v=>v.filter(n=>n.id!==id));setExpanded(v=>v===id?null:v);};
 const toasts=toastIds.map(id=>items.find(n=>n.id===id)).filter(Boolean) as Notice[];
 return <>
  <div className="notification-center" onMouseEnter={keepOpen} onMouseLeave={closeLater}>
   <button className={`notification-bell ${open?"active":""}`} onClick={()=>{clearTimeout(closeTimer.current);setOpen(v=>!v);}} aria-label="Abrir notificações" aria-expanded={open} title="Notificações"><Bell size={18}/>{visible.length>0&&<span className="notification-badge">{visible.length>99?"99+":visible.length}</span>}</button>
   {open&&<section className="notification-panel" onMouseEnter={keepOpen} onMouseLeave={closeLater} aria-label="Central de notificações">
    <div className="notification-panel-head"><div><strong>Notificações</strong><small>{visible.length?`${visible.length} registro(s)`:"Nenhuma notificação"}</small></div>{visible.length>0&&<button className="notification-clear" onClick={clearAll}><Trash2 size={14}/> Limpar</button>}</div>
    <div className="notification-list">{visible.length===0&&<div className="notification-empty"><Bell size={20}/><span>Nenhuma notificação registrada.</span></div>}{visible.map(item=>{const Icon=icons[item.level]||Info,isExpanded=expanded===item.id;return <article key={item.id} className={`notification-history ${item.level} ${isExpanded?"expanded":""}`} onClick={()=>setExpanded(isExpanded?null:item.id)}><Icon size={17}/><div className="notification-history-body"><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.timestamp).toLocaleString()} {item.source?`• ${item.source}`:""}</small>{isExpanded&&<div className="notification-details"><span><b>Quando:</b> {new Date(item.timestamp).toLocaleString()}</span><span><b>Origem:</b> {item.source||"Execução do sistema"}</span>{item.path&&<span><b>Local:</b> {item.path}</span>}{item.details&&<span><b>Detalhes:</b> {item.details}</span>}</div>}</div><button className="notification-close" onClick={e=>{e.stopPropagation();closeOne(item.id)}} aria-label="Fechar notificação"><X size={14}/></button></article>})}</div>
   </section>}
  </div>
  <div className="notification-toasts" aria-live="polite">{toasts.map(item=>{const Icon=icons[item.level]||Info;return <article key={item.id} className={`notification-toast ${item.level}`} onMouseEnter={()=>{clearTimeout(timers.current[item.id]);setPaused(v=>({...v,[item.id]:true}))}} onMouseLeave={()=>{setPaused(v=>({...v,[item.id]:false}));schedule(item.id)}}><Icon size={18}/><div><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.timestamp).toLocaleTimeString()}</small></div><button onClick={()=>dismiss(item.id)} aria-label="Fechar aviso"><X size={14}/></button><span className={`notification-timer ${paused[item.id]?"paused":""}`}/></article>})}</div>
 </>;
}
