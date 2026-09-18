import React,{useEffect,useState} from "react";
import {Palette,Plus,Trash2,Type,Image as ImageIcon,Heading,Paintbrush} from "lucide-react";
import {api} from "../../services/api";
import {Header,PanelTitle,Modal} from "../../components/Common";
import {BUILTIN,useTheme,Theme} from "../../components/ThemeProvider";
import type {User} from "../../types";

const blank=():Theme=>({id:"draft",name:"Novo tema",description:"",bg:"#071116",surface:"#102128",line:"#263943",ink:"#f4f7f8",muted:"#9baeb4",accent:"#46c3df",success:"#56d6a1",danger:"#f27777",menu:"#10232b",login:"#071116",fontFamily:"Inter, system-ui, sans-serif",fontSize:"16px",headingScale:"1",siteName:"M3U ARCHITECT",logo:"",title:"M3U ARCHITECT",h1:"Controle sua grade.",h2:"Canais e editor",h3:"Configurações"});

type Section="colors"|"typography"|"branding"|"headings";

export function ThemeSettingsPage({user}:{user:User}){
    const {themes,theme,setTheme,reload}=useTheme();
    const admin=user.role==="admin";
    const [open,setOpen]=useState(false);
    const [editingId,setEditingId]=useState<string|null>(null);
    const [draft,setDraft]=useState<Theme>(blank());
    const [section,setSection]=useState<Section>("colors");

    const startCreate=()=>{setEditingId(null);setDraft(blank());setSection("colors");setOpen(true)};
    const startEdit=(t:Theme)=>{if(!admin)return;setEditingId(t.id);setDraft({...blank(),...t});setSection("colors");setOpen(true)};
    const update=(key:keyof Theme,value:string)=>setDraft(d=>({...d,[key]:value}));
    const save=async()=>{
        if(!draft.name.trim())return;
        // A API atual cria temas; edição de temas existentes permanece segura no cliente
        // sem alterar os temas nativos. Para um tema existente, criamos uma nova versão.
        await api("/api/v1/themes",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:draft.name.trim(),description:draft.description,theme:draft})});
        await reload();
        setOpen(false);
    };
    const remove=async(id:string)=>{
        if(!confirm("Excluir este tema personalizado? Esta ação não pode ser desfeita."))return;
        await api(`/api/v1/themes/${id}`,{method:"DELETE"});
        if(theme.id===id)setTheme("default");
        await reload();
    };

    const colorFields:[keyof Theme,string][]=[
        ["bg","Fundo"],["surface","Superfície"],["line","Bordas"],["ink","Texto principal"],["muted","Texto secundário"],["accent","Destaque"],["success","Sucesso"],["danger","Erro"],["menu","Menu"],["login","Login"]
    ];
    return <>
        <Header kicker="APARÊNCIA" title="Temas" description="Escolha um tema ou crie uma identidade visual completa para o sistema.">
            {admin&&<button className="button primary" onClick={startCreate}><Plus size={15}/>Criar novo tema</button>}
        </Header>

        <div className="panel">
            <PanelTitle kicker="MEU TEMA" title="Tema deste usuário" badge={theme.name}/>
            <div className="theme-grid">
                {themes.map(t=><button key={t.id} className={`theme-card ${theme.id===t.id?"selected":""}`} onClick={()=>setTheme(t.id)} onDoubleClick={()=>startEdit(t)} title={admin?"Duplo clique para editar":"Clique para aplicar"}>
                    <span className="theme-preview" style={{background:t.bg,borderColor:t.line}}><i style={{background:t.accent}}/><i style={{background:t.success}}/><i style={{background:t.danger}}/></span>
                    <b>{t.name}</b><small>{t.description||"Tema disponível"}</small>
                </button>)}
            </div>
        </div>

        {admin&&<div className="panel">
            <PanelTitle kicker="ADMINISTRAÇÃO" title="Temas personalizados" badge="ADMIN"/>
            <div className="theme-admin-list">
                {themes.filter(t=>!BUILTIN.some(b=>b.id===t.id)).map(t=><div key={t.id}>
                    <span><Palette size={14}/><b>{t.name}</b></span>
                    <span><button className="text-button" onClick={()=>startEdit(t)}>Editar</button><button className="text-button danger-text" onClick={()=>remove(t.id)}><Trash2 size={13}/>Excluir</button></span>
                </div>)}
                {!themes.some(t=>!BUILTIN.some(b=>b.id===t.id))&&<p className="muted-text">Nenhum tema personalizado criado.</p>}
            </div>
        </div>}

        {open&&<Modal title={editingId?"Editar tema":"Criar novo tema"} close={()=>setOpen(false)}>
            <div className="theme-designer">
                <div className="theme-designer-sections">
                    <button className={section==="colors"?"active":""} onClick={()=>setSection("colors")}><Paintbrush size={15}/>Cores</button>
                    <button className={section==="typography"?"active":""} onClick={()=>setSection("typography")}><Type size={15}/>Fonte e tamanho</button>
                    <button className={section==="branding"?"active":""} onClick={()=>setSection("branding")}><ImageIcon size={15}/>Marca e título</button>
                    <button className={section==="headings"?"active":""} onClick={()=>setSection("headings")}><Heading size={15}/>H1, H2 e H3</button>
                </div>
                <div className="theme-designer-grid">
                    <div className="theme-options">
                        <label>Nome do tema<input value={draft.name} onChange={e=>update("name",e.target.value)}/></label>
                        {section==="colors"&&<div className="form-grid">{colorFields.map(([k,label])=><label key={k}>{label}<input type="color" value={String(draft[k]||"#000000")} onChange={e=>update(k,e.target.value)}/></label>)}</div>}
                        {section==="typography"&&<div className="form-grid">
                            <label>Família da fonte<select value={draft.fontFamily||"Inter, system-ui, sans-serif"} onChange={e=>update("fontFamily",e.target.value)}><option>Inter, system-ui, sans-serif</option><option>Arial, sans-serif</option><option>Georgia, serif</option><option>Verdana, sans-serif</option><option>monospace</option></select></label>
                            <label>Tamanho base<input type="text" value={draft.fontSize||"16px"} onChange={e=>update("fontSize",e.target.value)}/></label>
                            <label>Escala dos títulos<input type="text" value={draft.headingScale||"1"} onChange={e=>update("headingScale",e.target.value)}/></label>
                        </div>}
                        {section==="branding"&&<div className="form-grid">
                            <label>Nome do site<input value={draft.siteName||""} onChange={e=>update("siteName",e.target.value)}/></label>
                            <label>Título da página<input value={draft.title||""} onChange={e=>update("title",e.target.value)}/></label>
                            <label>Logo por URL<input value={draft.logo||""} onChange={e=>update("logo",e.target.value)} placeholder="https://..."/></label>
                        </div>}
                        {section==="headings"&&<div className="form-grid">
                            <label>Texto H1<input value={draft.h1||""} onChange={e=>update("h1",e.target.value)}/></label>
                            <label>Texto H2<input value={draft.h2||""} onChange={e=>update("h2",e.target.value)}/></label>
                            <label>Texto H3<input value={draft.h3||""} onChange={e=>update("h3",e.target.value)}/></label>
                        </div>}
                    </div>
                    <div className="theme-live-preview" style={{background:draft.bg,color:draft.ink,borderColor:draft.line,fontFamily:draft.fontFamily,fontSize:draft.fontSize}}>
                        <small style={{color:draft.accent}}>PRÉ-VISUALIZAÇÃO EM TEMPO REAL</small>
                        <div className="theme-preview-brand">{draft.logo&&<img src={draft.logo} alt="Logo" onError={e=>e.currentTarget.style.display="none"}/>}<strong>{draft.siteName||"M3U ARCHITECT"}</strong></div>
                        <h1 style={{fontSize:`calc(2rem * ${draft.headingScale||1})`}}>{draft.h1||"Título H1"}</h1>
                        <h2 style={{fontSize:`calc(1.5rem * ${draft.headingScale||1})`}}>{draft.h2||"Título H2"}</h2>
                        <h3 style={{fontSize:`calc(1.2rem * ${draft.headingScale||1})`}}>{draft.h3||"Título H3"}</h3>
                        <p style={{color:draft.muted}}>Texto secundário de exemplo para visualizar contraste, fonte e escala.</p>
                        <div className="theme-preview-buttons"><button style={{background:draft.accent,color:draft.bg}}>Ação principal</button><button style={{background:draft.surface,color:draft.ink,border:`1px solid ${draft.line}`}}>Secundário</button></div>
                    </div>
                </div>
                <div className="modal-actions"><button className="button subtle" onClick={()=>setOpen(false)}>Cancelar</button><button className="button primary" onClick={save}>{editingId?"Salvar nova versão":"Criar tema"}</button></div>
            </div>
        </Modal>}
    </>;
}
