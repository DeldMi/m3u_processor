import React,{useEffect} from "react";
import {api} from "../../services/api";
import type {Channel,User} from "../../types";

/** Recupera o ID interno pelo nome exibido na tabela. */
async function resolveChannelId(name:string):Promise<number|null>{
    const rows=await api<Channel[]>(`/api/v1/channels?search=${encodeURIComponent(name)}`);
    const exact=rows.find(row=>row.name===name);
    return exact?.id ?? rows[0]?.id ?? null;
}

/**
 * Complemento administrativo da página legada de canais.
 * Mantém filtros, seleção, edição e criação de playlists intactos e adiciona
 * apenas exclusão unitária e em lote com confirmação explícita.
 */
export function ChannelAdminActions({user}:{user:User}){
    const allowed=user.role==="admin" || Boolean(user.permissions?.channels?.includes("delete"));
    useEffect(()=>{
        if(!allowed)return;
        let observer:MutationObserver|undefined;
        const enhance=()=>{
            const root=document.querySelector(".table-panel");
            if(!root)return;
            Array.from(root.querySelectorAll("tbody tr")).forEach(row=>{
                const actionCell=row.querySelector("td:last-child");
                if(!actionCell || actionCell.querySelector("[data-channel-admin-delete]"))return;
                const name=row.querySelector(".channel-name b")?.textContent?.trim();
                if(!name)return;
                const button=document.createElement("button");
                button.className="text-button danger-text";
                button.type="button";
                button.dataset.channelAdminDelete="1";
                button.title=`Excluir ${name}`;
                button.textContent="Excluir";
                button.addEventListener("click",async()=>{
                    if(!confirm(`Excluir o canal \"${name}\"? Esta ação não pode ser desfeita.`))return;
                    try{
                        const id=await resolveChannelId(name);
                        if(id===null)throw new Error("Canal não encontrado");
                        await api(`/api/v1/channels/${id}`,{method:"DELETE"});
                        window.location.reload();
                    }catch(error){console.error(error);alert("Não foi possível excluir o canal.")}
                });
                actionCell.appendChild(button);
            });
            const toolbar=root.querySelector(".editor-actions");
            if(toolbar && !toolbar.querySelector("[data-channel-admin-bulk]")){
                const button=document.createElement("button");
                button.className="button subtle";
                button.type="button";
                button.dataset.channelAdminBulk="1";
                button.textContent="Excluir selecionados";
                button.addEventListener("click",async()=>{
                    const selectedRows=Array.from(root.querySelectorAll("tbody tr")).filter(row=>row.querySelector<HTMLInputElement>('td:first-child input[type="checkbox"]')?.checked);
                    if(!selectedRows.length){alert("Selecione pelo menos um canal.");return}
                    const names=selectedRows.map(row=>row.querySelector(".channel-name b")?.textContent?.trim()).filter(Boolean) as string[];
                    if(!confirm(`Excluir ${names.length} canal(is) selecionado(s)? Esta ação não pode ser desfeita.`))return;
                    try{
                        for(const name of names){const id=await resolveChannelId(name);if(id!==null)await api(`/api/v1/channels/${id}`,{method:"DELETE"})}
                        window.location.reload();
                    }catch(error){console.error(error);alert("Alguns canais não puderam ser excluídos.")}
                });
                toolbar.appendChild(button);
            }
        };
        const timer=window.setTimeout(()=>{
            enhance();
            observer=new MutationObserver(enhance);
            observer.observe(document.querySelector(".main-content")||document.body,{childList:true,subtree:true});
        },0);
        return()=>{window.clearTimeout(timer);observer?.disconnect()};
    },[allowed]);
    return null;
}
