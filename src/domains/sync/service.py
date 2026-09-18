"""Serviço de execução do pipeline de sincronização M3U."""
import asyncio
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from collections import deque
from typing import Any, Callable
from src.domains.health.internet import check_internet_health

class PipelineInterrupted(Exception):
    """Sinaliza cancelamento solicitado pelo usuário."""

def _publication_snapshot(output_dir: str):
    backup=tempfile.TemporaryDirectory(prefix="m3u-publication-");previous={}
    for name in os.listdir(output_dir):
        source=os.path.join(output_dir,name)
        if os.path.isfile(source):
            target=os.path.join(backup.name,"previous",name);os.makedirs(os.path.dirname(target),exist_ok=True);shutil.copy2(source,target);previous[name]=target
    return backup,previous

def _apply_publication_policy(output_dir,backup_dir,previous,mode,generated_names):
    """Publica somente arquivos derivados da execução atual e nunca apaga fora de output."""
    generated={};generated_root=os.path.join(backup_dir,"generated");os.makedirs(generated_root,exist_ok=True)
    for name in generated_names:
        source=os.path.join(output_dir,name)
        if os.path.isfile(source):target=os.path.join(generated_root,name);shutil.copy2(source,target);generated[name]=target
    for name in os.listdir(output_dir):
        path=os.path.join(output_dir,name)
        if os.path.isfile(path):os.remove(path)
    for name,source in previous.items():shutil.copy2(source,os.path.join(output_dir,name))
    if mode=="CREATE":allowed=[n for n in generated if n not in previous]
    elif mode=="UPDATE":allowed=[n for n in generated if n in previous]
    else:allowed=list(generated)
    for name in allowed:shutil.copy2(generated[name],os.path.join(output_dir,name))

def execute_pipeline(*,manager:Any,process_state:dict[str,Any],process_logs:deque,pause_requested:threading.Event,stop_requested:threading.Event,pipeline_lock:threading.Lock,state:dict[str,Any],min_free_space_bytes:int,update_log:Callable,publication_mode:str="NONE"):
    if process_state["status"]=="Executando..." or not pipeline_lock.acquire(blocking=False):return
    active_run_id=None;loop=None;mode=(publication_mode or "NONE").upper();backup_ctx=None;previous_files={}
    def checkpoint(_stage):
        if stop_requested.is_set():raise PipelineInterrupted("Execução interrompida pelo usuário.")
        while pause_requested.is_set() and not stop_requested.is_set():process_state["status"]="Pausado";time.sleep(.2)
        if stop_requested.is_set():raise PipelineInterrupted("Execução interrompida pelo usuário.")
        if process_state["status"]=="Pausado":process_state["status"]="Executando...";update_log("Execução retomada.","info",active_run_id)
    try:
        if shutil.disk_usage(manager.base_dir).free<min_free_space_bytes:process_state["status"]="Erro";process_state["ultimo_log"]="Espaço em disco insuficiente para executar a sincronização.";return
        stop_requested.clear();pause_requested.clear();active_run_id=manager.db.start_process_run();state["active_run_id"]=active_run_id;process_state["status"]="Executando...";process_state["publication_mode"]=mode;update_log(f"Iniciando auditoria completa. Publicação: {mode}.","info",active_run_id)
        if mode in {"CREATE","UPDATE","CREATE_UPDATE"}:backup_ctx,previous_files=_publication_snapshot(manager.output_dir)
        loop=asyncio.new_event_loop();asyncio.set_event_loop(loop)
        result=loop.run_until_complete(manager.sync_and_audit(progress_callback=lambda message:update_log(message,"info",active_run_id),control_callback=checkpoint,publication_mode=mode))
        if backup_ctx is not None:
            generated_names={n for m in result.get("partitions",[]) for n in (m.get("m3u_name"),m.get("xml_name")) if n};_apply_publication_policy(manager.output_dir,backup_ctx.name,previous_files,mode,generated_names)
            if mode=="CREATE":result["partitions"]=[m for m in result.get("partitions",[]) if m.get("m3u_name") not in previous_files]
            elif mode=="UPDATE":result["partitions"]=[m for m in result.get("partitions",[]) if m.get("m3u_name") in previous_files]
        process_state.update({"total_canais":result.get("total",0),"canais_online":result.get("online",0),"canais_offline":result.get("offline",0),"manifestos":result.get("partitions",[]),"status":"Concluido"});process_state["ultimo_log"]=f"Sucesso! {result.get('online',0)} canais operantes. {len(result.get('partitions',[]))} publicação(ões) aplicadas. Log: {result.get('log_file')}";update_log(process_state["ultimo_log"],"success",active_run_id);manager.db.finish_process_run(active_run_id,"Concluido",result,process_state["ultimo_log"])
    except PipelineInterrupted as exc:
        process_state["status"]="Interrompido";process_state["ultimo_log"]=str(exc);update_log(process_state["ultimo_log"],"warning",active_run_id)
        if active_run_id is not None:manager.db.finish_process_run(active_run_id,"Interrompido",{},process_state["ultimo_log"])
    except (OSError,sqlite3.OperationalError) as exc:
        process_state["status"]="Erro";process_state["ultimo_log"]="Falha de armazenamento durante a execução. Libere espaço em disco e tente novamente.";update_log(process_state["ultimo_log"],"error",active_run_id)
        if active_run_id is not None:
            try:manager.db.finish_process_run(active_run_id,"Erro",{},process_state["ultimo_log"])
            except (OSError,sqlite3.OperationalError):pass
    except Exception as exc:
        process_state["status"]="Erro";process_state["ultimo_log"]=f"Falha na execucao: {exc}";update_log(process_state["ultimo_log"],"error",active_run_id)
        if active_run_id is not None:manager.db.finish_process_run(active_run_id,"Erro",{},process_state["ultimo_log"])
    finally:
        pause_requested.clear();stop_requested.clear();state["active_run_id"]=None
        if backup_ctx is not None:backup_ctx.cleanup()
        if loop is not None:loop.close()
        pipeline_lock.release()

def execute_health_check(*,manager:Any,process_state:dict[str,Any],pipeline_lock:threading.Lock):
    if pipeline_lock.locked() or shutil.disk_usage(manager.base_dir).free<512*1024*1024:return
    internet=check_internet_health(manager.config_mgr.get_all());process_state["internet_online"]=bool(internet.get("online"));process_state["internet_latency_ms"]=internet.get("latency_ms",0)
    if not internet.get("online"):process_state["ultimo_log"]="Verificação de canais não executada: Internet indisponível.";return
    try:
        result=asyncio.run(manager.refresh_channel_health());process_state.update({"total_canais":result["total"],"canais_online":result["online"],"canais_offline":result["offline"]});process_state["ultimo_log"]=f"Saúde atualizada: {result['online']} online, {result['offline']} offline."
    except (OSError,sqlite3.OperationalError):return
