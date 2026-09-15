import os
import threading
import asyncio
from flask import Flask, render_template_string, jsonify, request, send_from_directory, abort
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
    "manifestos": [],
    "ultimo_log": "Sistema pronto para execucao."
}

def execute_pipeline():
    global PROCESS_STATE
    if PROCESS_STATE["status"] == "Executando...":
        return

    PROCESS_STATE["status"] = "Executando..."
    PROCESS_STATE["ultimo_log"] = "Deduplicando e coletando canais (locais, historicos e remotos)..."

    channels = asyncio.run(manager.load_all_channels())
    total = len(channels)
    PROCESS_STATE["total_canais"] = total

    if total == 0:
        PROCESS_STATE["status"] = "Finalizado (Vazio)"
        PROCESS_STATE["ultimo_log"] = "Nenhum canal localizado para validar."
        return

    PROCESS_STATE["ultimo_log"] = f"Validando integridade de {total} canais unicos com bypass SSL..."
    valid, invalid = asyncio.run(manager.validate_channels(channels))

    PROCESS_STATE["canais_online"] = len(valid)
    PROCESS_STATE["canais_offline"] = len(invalid)

    PROCESS_STATE["ultimo_log"] = "Particionando lotes de no maximo 400 canais e sincronizando EPGs..."
    manifests = asyncio.run(manager.process_and_partition(valid))
    PROCESS_STATE["manifestos"] = manifests

    log_path = manager.generate_audit_log(total, valid, invalid, manifests)
    PROCESS_STATE["status"] = "Concluido"
    PROCESS_STATE["ultimo_log"] = f"Finalizado! {len(valid)} ativos salvos em {len(manifests)} bloco(s). Removidos: {len(invalid)}. Log: {os.path.basename(log_path)}"

def setup_scheduler():
    scheduler.remove_all_jobs()
    cfg = config_mgr.get_all()
    mode = cfg["SCHEDULE_MODE"]

    if mode == "INTERVAL":
        hours = max(1, cfg["SCHEDULE_INTERVAL_HOURS"])
        scheduler.add_job(execute_pipeline, 'interval', hours=hours, id="m3u_job")
    elif mode == "CRON":
        try:
            h, m = cfg["SCHEDULE_CRON_TIME"].split(":")
            scheduler.add_job(execute_pipeline, 'cron', hour=int(h), minute=int(m), id="m3u_job")
        except Exception:
            pass

setup_scheduler()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Painel de Controle M3U e Guia EPG</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }
        .container { max-width: 1100px; margin: 0 auto; }
        .card { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }
        h1, h2, h3 { color: #38bdf8; margin-top: 0; }
        .grid-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        .metric { background: #0f172a; padding: 16px; border-radius: 6px; text-align: center; border: 1px solid #1e293b; }
        .metric-title { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
        .metric-value { font-size: 24px; font-weight: bold; margin-top: 6px; }
        .btn { background: #0284c7; color: #fff; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; }
        .btn:hover { background: #0369a1; }
        .btn:disabled { background: #475569; cursor: not-allowed; }
        pre { background: #000; padding: 12px; border-radius: 6px; color: #4ade80; font-size: 12px; max-height: 140px; overflow-y: auto; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-size: 13px; color: #94a3b8; margin-bottom: 5px; }
        input, select, textarea { width: 100%; padding: 10px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 6px; box-sizing: border-box; }
        textarea { height: 65px; resize: vertical; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #334155; font-size: 13px; }
        th { color: #94a3b8; }
        .link-copy { background: #0f172a; padding: 4px 8px; border-radius: 4px; border: 1px solid #334155; font-family: monospace; color: #38bdf8; word-break: break-all; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h1>Painel Gerenciador de Listas e Guias EPG</h1>
        <div class="grid-metrics">
            <div class="metric"><div class="metric-title">Status</div><div class="metric-value" id="status">Ocioso</div></div>
            <div class="metric"><div class="metric-title">Total Processado</div><div class="metric-value" id="total">0</div></div>
            <div class="metric"><div class="metric-title">Operantes</div><div class="metric-value" style="color: #4ade80;" id="online">0</div></div>
            <div class="metric"><div class="metric-title">Removidos / Offline</div><div class="metric-value" style="color: #f87171;" id="offline">0</div></div>
        </div>
        <button class="btn" id="btn-run" onclick="iniciarProcessamento()">Processar e Reorganizar Agora</button>
    </div>

    <div class="card">
        <h2>Links dos Arquivos Gerados (Diretos para Player / IPTV)</h2>
        <table id="links-table">
            <thead>
                <tr>
                    <th>Partição</th>
                    <th>Canais</th>
                    <th>Link M3U / M3U8</th>
                    <th>Link Guia EPG (XMLTV)</th>
                </tr>
            </thead>
            <tbody id="links-body">
                <tr><td colspan="4" style="text-align: center; color: #94a3b8;">Nenhum lote gerado até o momento.</td></tr>
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2>Configurações do Ambiente e Automação (.env)</h2>
        <div class="form-row">
            <div class="form-group">
                <label>Modo de Repetição / Agendador:</label>
                <select id="cfg-schedule-mode">
                    <option value="DISABLED">Desativado (Manual)</option>
                    <option value="INTERVAL">Por Intervalo (Horas)</option>
                    <option value="CRON">Horário Fixo Diário</option>
                </select>
            </div>
            <div class="form-group">
                <label>Parâmetro de Tempo:</label>
                <input type="text" id="cfg-schedule-val" placeholder="Ex: 12 (horas) ou 03:00 (horário diário)">
            </div>
        </div>

        <div class="form-row">
            <div class="form-group">
                <label>URL Base Pública do Servidor (BASE_URL):</label>
                <input type="text" id="cfg-base-url" placeholder="http://127.0.0.1:5000">
            </div>
            <div class="form-group">
                <label>Máximo de Canais por Arquivo:</label>
                <input type="number" id="cfg-max-channels" value="400">
            </div>
        </div>

        <div class="form-group">
            <label>Links de Listas M3U Remotas (Separadas por ';'):</label>
            <textarea id="cfg-m3u-urls" placeholder="http://servidor.com/lista.m3u; https://outro.com/lista.m3u8"></textarea>
        </div>

        <div class="form-group">
            <label>Links de Guias EPG XMLTV (iptv-epg.org ou outros, separados por ';'):</label>
            <textarea id="cfg-epg-urls" placeholder="https://iptv-epg.org/files/brazil.xml.gz; https://iptv-epg.org/files/portugal.xml.gz"></textarea>
        </div>

        <button class="btn" style="background: #10b981;" onclick="salvarConfiguracoes()">Salvar Configurações no .env</button>
    </div>

    <div class="card">
        <h3>Log de Operações em Tempo Real</h3>
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
            document.getElementById('cfg-base-url').value = data.BASE_URL;
            document.getElementById('cfg-max-channels').value = data.MAX_CHANNELS_PER_FILE;
            document.getElementById('cfg-m3u-urls').value = data.REMOTE_M3U_URLS;
            document.getElementById('cfg-epg-urls').value = data.EPG_URLS;
        });
}

function salvarConfiguracoes() {
    const mode = document.getElementById('cfg-schedule-mode').value;
    const val = document.getElementById('cfg-schedule-val').value;

    const payload = {
        SCHEDULE_MODE: mode,
        BASE_URL: document.getElementById('cfg-base-url').value,
        MAX_CHANNELS_PER_FILE: document.getElementById('cfg-max-channels').value,
        REMOTE_M3U_URLS: document.getElementById('cfg-m3u-urls').value,
        EPG_URLS: document.getElementById('cfg-epg-urls').value
    };

    if (mode === 'INTERVAL') payload.SCHEDULE_INTERVAL_HOURS = val;
    if (mode === 'CRON') payload.SCHEDULE_CRON_TIME = val;

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(res => res.json()).then(() => {
        alert("Configurações salvas e agendador sincronizado!");
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

            const tbody = document.getElementById('links-body');
            if (data.manifestos.length > 0) {
                tbody.innerHTML = data.manifestos.map(m => `
                    <tr>
                        <td><b>${m.m3u_name}</b></td>
                        <td>${m.total_canais}</td>
                        <td><a class="link-copy" href="${m.m3u_url}" target="_blank">${m.m3u_url}</a></td>
                        <td><a class="link-copy" href="${m.xml_url}" target="_blank">${m.xml_url}</a></td>
                    </tr>
                `).join('');
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

# Rotas diretas para download/streaming de listas e EPGs
@app.route("/playlist/<filename>")
def serve_playlist(filename):
    return send_from_directory(manager.output_dir, filename, mimetype="application/x-mpegurl")

@app.route("/epg/<filename>")
def serve_epg(filename):
    return send_from_directory(manager.output_dir, filename, mimetype="application/xml")

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