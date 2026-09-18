import React,{useEffect} from "react";
import {Trash2} from "lucide-react";
import {api,send} from "../../services/api";
import type {Channel,User} from "../../types";

/**
 * Recupera o ID interno pelo nome exibido na tabela.
 * A página legada já controla seleção/filtros/paginação; este complemento
 * adiciona apenas as ações administrativas sem substituir essa lógica.
 */
async function resolveChannelId(name:string):Promise<number|null>{
    const rows=await api<Channel[]>(`/api/v1/channels?search=${encodeURIComponent(name)}`);
    const exact=rows.find(row=>row.name===name);
    return exact?.id ?? rows[0]?.id ?? null;
}

export function ChannelAdminActions({user}:{user:User}){
    const allowed=user.role==="admin" || Boolean(user.permissions?.channels?.includes("delete"));
    useEffect(()=>{
        if(!allowed)return;
        let observer:MutationObserver|undefined;
        const enhance=()=>{
            const root=document.querySelector(".table-panel");
            if(!root)return;
            const rows=Array.from(root.querySelectorAll("tbody tr"));
            rows.forEach(row=>{
                const actionCell=row.querySelector("td:last-child");
                if(!actionCell || actionCell.querySelector("[data-channel-admin-delete]"))return;
                const name=row.querySelector(".channel-name b")?.textContent?.trim();
                if(!name)return;
                const button=document.createElement("button");
                button.className="text-button danger-text";
                button.type="button";
                button.dataset.channelAdminDelete="1";
                button.title=`Excluir ${name}`;
                button.innerHTML="<span aria-hidden=\"true\">×</span> Excluir";
                button.addEventListener("click",async()=>{
                    if(!confirm(`Excluir o canal \"${name}\"? Esta ação não pode ser desfeita.`))return;
                    try{
                        const id=await resolveChannelId(name);
                        if(id===null)throw new Error("Canal não encontrado");
                        await send(`/api/v1/channels/${id}`,{method:"DELETE"});
                        window.location.reload();
                    }catch(error){
                        console.error(error);
                        alert("Não foi possível excluir o canal.");
                    }
                });
                actionCell.appendChild(button);
            });

            const toolbar=root.querySelector(".editor-actions");
            if(toolbar && !toolbar.querySelector("[data-channel-admin-bulk]")){
                const button=document.createElement("button");
                button.className="button subtle";
                button.type="button";
                button.dataset.channelAdminBulk="1";
                button.innerHTML="<span aria-hidden=\"true\">×</span> Excluir selecionados";
                button.addEventListener("click",async()=>{
                    const selectedRows=Array.from(root.querySelectorAll("tbody tr")).filter(row=>{
                        const checkbox=row.querySelector<HTMLInputElement>('td:first-child input[type="checkbox"]');
                        return Boolean(checkbox?.checked);
                    });
                    if(!selectedRows.length){alert("Selecione pelo menos um canal.");return;}
                    const names=selectedRows.map(row=>row.querySelector(".channel-name b")?.textContent?.trim()).filter(Boolean) as string[];
                    if(!confirm(`Excluir ${names.length} canal(is) selecionado(s)? Esta ação não pode ser desfeita.`))return;
                    try{
                        for(const name of names){
                            const id=await resolveChannelId(name);
                            if(id!==null)await send(`/api/v1/channels/${id}`,{method:"DELETE"});
                        }
                        window.location.reload();
                    }catch(error){
                        console.error(error);
                        alert("Alguns canais não puderam ser excluídos.");
                    }
                });
                toolbar.appendChild(button);
            }
        };
        const start=()=>{
            enhance();
            observer=new MutationObserver(enhance);
            const root=document.querySelector(".main-content")||document.body;
            observer.observe(root,{childList:true,subtree:true});
        };
        const timer=window.setTimeout(start,0);
        return()=>{window.clearTimeout(timer);observer?.disconnect()};
    },[allowed]);
    return null;
}
