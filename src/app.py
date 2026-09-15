import os
import threading
import asyncio
from flask import Flask, render_template_string, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from src.manager import PlaylistManager
from src.config import ConfigManager

app = Flask(__name__)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
manager = PlaylistManager(ROOT_DIR)
config_mgr = ConfigManager(ROOT_DIR)

scheduler = BackgroundScheduler(daemon=True)
scheduler.start()

PROCESS_STATE = {
    "status": "Ocioso",
    "total_canais": 0,
    "canais_online": 0,
    "canais_offline": 0,
    "arquivos_gerados": [],
    "ultimo_log": "Pronto para execucao."
}

def execute_pipeline():
    global PROCESS_STATE
    if PROCESS_STATE["status"] == "Executando...":
        return

    PROCESS_STATE["status"] = "Executando..."
    PROCESS_STATE["ultimo_log"] = "Carregando canais locais e remotos..."

    channels = asyncio.run(manager.load_all_channels())
    total = len(channels)
    PROCESS_STATE["total_canais"] = total

    if total == 0:
        PROCESS_STATE["status"] = "Finalizado (Vazio)"
        PROCESS_STATE["ultimo_log"] = "Nenhum canal encontrado nas fontes locais ou remotas."
        return

    PROCESS_STATE["ultimo_log"] = f"Validando {total} canais de forma concorrente..."
    valid, invalid = asyncio.run(manager.validate_channels(channels))

    PROCESS_STATE["canais_online"] = len(valid)
    PROCESS_STATE["canais_offline"] = len(invalid)

    PROCESS_STATE["ultimo_log"] = "Particionando canais em lotes..."
    created_files = manager.save_partitioned_playlists(valid)
    PROCESS_STATE["arquivos_gerados"] = created_files

    log_path = manager.generate_audit_log(total, valid, invalid, created_files)
    PROCESS_STATE["status"] = "Concluido"
    PROCESS_STATE["ultimo_log"] = f"Sucesso! {len(valid)} canais ativos distribuídos em {len(created_files)} arquivo(s). Log: {os.path.basename(log_path)}"

def setup_scheduler():
    scheduler.remove_all_jobs()
    cfg = config_mgr.get_all()
    mode = cfg["SCHEDULE_MODE"]

    if mode == "INTERVAL":
        hours = max(1, cfg["SCHEDULE_INTERVAL_HOURS"])
        scheduler.add_job(execute_pipeline, 'interval', hours=hours, id="m3u_job")
    elif mode == "CRON":
        cron_time = cfg["SCHEDULE_CRON_TIME"]
        try:
            h, m = cron_time.split(":")
            scheduler.add_job(execute_pipeline, 'cron', hour=int(h), minute=int(m), id="m3u_job")
        except Exception:
            pass

# Configura o agendamento inicial baseado no .env
setup_scheduler()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Painel de Controle e Auditoria M3U</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .card { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }
        h1, h2, h3 { color: #38bdf8; margin-top: 0; }
        .grid-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .metric { background: #0f172a; padding: 16px; border-radius: 6px; text-align: center; border: 1px solid #1e293b; }
        .metric-title { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
        .metric-value { font-size: 24px; font-weight: bold; margin-top: 6px; }
        .btn { background: #0284c7; color: #fff; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; }
        .btn:hover { background: #0369a1; }
        .btn:disabled { background: #475569; cursor: not-allowed; }
        pre { background: #000; padding: 12px; border-radius: 6px; color: #4ade80; font-size: 12px; max-height: 180px; overflow-y: auto; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-size: 13px; color: #94a3b8; margin-bottom: 5px; }
        input, select, textarea { width: 100%; padding: 10px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 6px; box-sizing: border-box; }
        textarea { height: 75px; resize: vertical; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h1>Painel de Controle M3U/M3U8</h1>
        <div class="grid-metrics">
            <div class="metric"><div class="metric-title">Status</div><div class="metric-value" id="status">Ocioso</div></div>
            <div class="metric"><div class="metric-title">Total Lido</div><div class="metric-value" id="total">0</div></div>
            <div class="metric"><div class="metric-title">Operantes</div><div class="metric-value" style="color: #4ade80;" id="online">0</div></div>
            <div class="metric"><div class="metric-title">Inoperantes</div><div class="metric-value" style="color: #f87171;" id="offline">0</div></div>
        </div>
        <button class="btn" id="btn-run" onclick="iniciarProcessamento()">Processar Agora</button>
    </div>

    <div class="card">
        <h2>Configurações do Ambiente (.env)</h2>
        <div class="form-row">
            <div class="form-group">
                <label>Modo de Agendamento Automático:</label>
                <select id="cfg-schedule-mode">
                    <option value="DISABLED">Desativado (Execução Manual)</option>
                    <option value="INTERVAL">Por Intervalo Regular</option>
                    <option value="CRON">Horário Diário Fixo</option>
                </select>
            </div>
            <div class="form-group">
                <label>Parâmetro de Tempo:</label>
                <input type="text" id="cfg-schedule-val" placeholder="Ex: 12 (horas) ou 03:00 (diário)">
            </div>
        </div>

        <div class="form-row">
            <div class="form-group">
                <label>Máximo de Canais por Arquivo (Default: 400):</label>
                <input type="number" id="cfg-max-channels">
            </div>
            <div class="form-group">
                <label>Limite de Conexões Simultâneas (Concorrência):</label>
                <input type="number" id="cfg-concurrency">
            </div>
        </div>

        <div class="form-group">
            <label>Timeout por Canal (Segundos):</label>
            <input type="number" id="cfg-timeout">
        </div>

        <div class="form-group">
            <label>Listas Remotas (URLs separadas por ponto e vírgula ';'):</label>
            <textarea id="cfg-urls" placeholder="http://exemplo.com/lista1.m3u; http://exemplo.com/lista2.m3u8"></textarea>
        </div>

        <button class="btn" style="background: #10b981;" onclick="salvarConfiguracoes()">Salvar Configurações</button>
    </div>

    <div class="card">
        <h3>Arquivos Gerados na Pasta Output</h3>
        <ul id="files-list" style="color: #38bdf8;"><li>Nenhum arquivo gerado nesta sessão.</li></ul>
        <h3>Console de Eventos</h3>
        <pre id="log-output">Pronto.</pre>
    </div>
</div>

<script>
function carregarConfig() {
    fetch('/api/config')
        .then(res => res.json())
        .then(data => {
            document.getElementById('cfg-schedule-mode').value = data.SCHEDULE_MODE;
            document.getElementById('cfg-schedule-val').value = (data.SCHEDULE_MODE === 'INTERVAL') ? data.SCHEDULE_INTERVAL_HOURS : data.SCHEDULE_CRON_TIME;
            document.getElementById('cfg-max-channels').value = data.MAX_CHANNELS_PER_FILE;
            document.getElementById('cfg-concurrency').value = data.CONCURRENCY_LIMIT;
            document.getElementById('cfg-timeout').value = data.REQUEST_TIMEOUT;
            document.getElementById('cfg-urls').value = data.REMOTE_M3U_URLS;
        });
}

function salvarConfiguracoes() {
    const mode = document.getElementById('cfg-schedule-mode').value;
    const val = document.getElementById('cfg-schedule-val').value;

    const payload = {
        SCHEDULE_MODE: mode,
        MAX_CHANNELS_PER_FILE: document.getElementById('cfg-max-channels').value,
        CONCURRENCY_LIMIT: document.getElementById('cfg-concurrency').value,
        REQUEST_TIMEOUT: document.getElementById('cfg-timeout').value,
        REMOTE_M3U_URLS: document.getElementById('cfg-urls').value
    };

    if (mode === 'INTERVAL') {
        payload.SCHEDULE_INTERVAL_HOURS = val;
    } else if (mode === 'CRON') {
        payload.SCHEDULE_CRON_TIME = val;
    }

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(res => res.json()).then(() => {
        alert("Configurações persistidas com sucesso no .env!");
        carregarConfig();
    });
}

function atualizarDados() {
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            document.getElementById('status').innerText = data.status;
            document.getElementById('total').innerText = data.total_canais;
            document.getElementById('online').innerText = data.canais_online;
            document.getElementById('offline').innerText = data.canais_offline;
            document.getElementById('log-output').innerText = data.ultimo_log;
            
            document.getElementById('btn-run').disabled = (data.status === "Executando...");

            const listEl = document.getElementById('files-list');
            if (data.arquivos_gerados.length > 0) {
                listEl.innerHTML = data.arquivos_gerados.map(f => `<li>${f}</li>`).join('');
            }
        });
}

function iniciarProcessamento() {
    fetch('/api/start', { method: 'POST' });
}

carregarConfig();
setInterval(atualizarDados, 2000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/status")
def get_status():
    return jsonify(PROCESS_STATE)

@app.route("/api/start", methods=["POST"])
def start_execution():
    if PROCESS_STATE["status"] != "Executando...":
        thread = threading.Thread(target=execute_pipeline, daemon=True)
        thread.start()
        return jsonify({"status": "iniciado"})
    return jsonify({"status": "em_andamento"})

@app.route("/api/config", methods=["GET", "POST"])
def manage_config():
    if request.method == "POST":
        data = request.json or {}
        for k, v in data.items():
            config_mgr.update_key(k, v)
        setup_scheduler()
        return jsonify({"status": "atualizado"})
    return jsonify(config_mgr.get_all())

if __name__ == "__main__":
    cfg = config_mgr.get_all()
    app.run(host=cfg["WEB_HOST"], port=cfg["WEB_PORT"], debug=False)