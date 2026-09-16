import React, { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { api } from "../../services/api";
import type { InternetHealth } from "../../types";
import { Header, PanelTitle } from "../../components/Common";


export function SettingsPage() {
    const [config, setConfig] = useState<Record<string, string | number>>({});
    const [saved, setSaved] = useState(false);
    useEffect(() => {
        api<Record<string, string | number>>("/api/config")
            .then(setConfig)
            .catch(() => undefined);
    }, []);
    const set = (k: string, v: string) => setConfig({ ...config, [k]: v });
    const save = () =>
        api("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config),
        }).then(() => {
            setSaved(true);
            setTimeout(() => setSaved(false), 2500);
        });
    return (
        <>
            <Header
                kicker="SISTEMA"
                title="Configurações"
                description="Parâmetros de execução, distribuição e integrações."
            />
            <div className="panel settings-panel">
                <PanelTitle kicker="AMBIENTE" title="Parâmetros operacionais" />
                <div className="form-grid">
                    <label>
                        Modo de automação
                        <select
                            value={String(config.SCHEDULE_MODE || "DISABLED")}
                            onChange={(e) => set("SCHEDULE_MODE", e.target.value)}
                        >
                            <option value="DISABLED">Desativado (manual)</option>
                            <option value="INTERVAL">Por intervalo regular</option>
                            <option value="CRON">Horário fixo diário</option>
                        </select>
                    </label>
                    <label>
                        Tempo (horas ou HH:MM)
                        <input
                            value={String(
                                config.SCHEDULE_MODE === "INTERVAL"
                                    ? config.SCHEDULE_INTERVAL_HOURS || ""
                                    : config.SCHEDULE_CRON_TIME || "",
                            )}
                            onChange={(e) =>
                                set(
                                    config.SCHEDULE_MODE === "INTERVAL"
                                        ? "SCHEDULE_INTERVAL_HOURS"
                                        : "SCHEDULE_CRON_TIME",
                                    e.target.value,
                                )
                            }
                        />
                    </label>
                    <label>
                        URL do menu
                        <input
                            value={String(config.BASE_URL || "")}
                            onChange={(e) => set("BASE_URL", e.target.value)}
                        />
                    </label>
                    <label>
                        URL dos links públicos
                        <input
                            value={String(config.PUBLIC_BASE_URL || "")}
                            onChange={(e) => set("PUBLIC_BASE_URL", e.target.value)}
                        />
                    </label>
                    <label>
                        Porta do menu
                        <input
                            type="number"
                            value={String(config.WEB_PORT || "")}
                            onChange={(e) => set("WEB_PORT", e.target.value)}
                        />
                    </label>
                    <label>
                        Porta dos links
                        <input
                            type="number"
                            value={String(config.PUBLIC_PORT || "")}
                            onChange={(e) => set("PUBLIC_PORT", e.target.value)}
                        />
                    </label>
                    <label>
                        Capacidade máxima por lista
                        <input
                            type="number"
                            value={String(config.MAX_CHANNELS_PER_FILE || "")}
                            onChange={(e) => set("MAX_CHANNELS_PER_FILE", e.target.value)}
                        />
                    </label>
                    <label>
                        Concorrência de verificação
                        <input
                            type="number"
                            value={String(config.CONCURRENCY_LIMIT || "")}
                            onChange={(e) => set("CONCURRENCY_LIMIT", e.target.value)}
                        />
                    </label>
                    <label>
                        Timeout de requisição
                        <input
                            type="number"
                            value={String(config.REQUEST_TIMEOUT || "")}
                            onChange={(e) => set("REQUEST_TIMEOUT", e.target.value)}
                        />
                    </label>
                    <label>
                        Token da API externa
                        <input
                            value={String(config.API_TOKEN || "")}
                            onChange={(e) => set("API_TOKEN", e.target.value)}
                        />
                    </label>
                    <label>
                        User-Agent
                        <input
                            value={String(config.USER_AGENT || "")}
                            onChange={(e) => set("USER_AGENT", e.target.value)}
                        />
                    </label>
                    <label>Saúde automática (segundos)<input type="number" min="15" value={String(config.HEALTH_CHECK_INTERVAL_SECONDS || "")} onChange={(e) => set("HEALTH_CHECK_INTERVAL_SECONDS", e.target.value)} /></label>
                    <label>Atualização automática do xTeVe<select value={String(config.AUTO_UPDATE_XTEVE || "0")} onChange={(e) => set("AUTO_UPDATE_XTEVE", e.target.value)}><option value="0">Desativada</option><option value="1">Ativada</option></select></label>
                    <label>Número de tuners<input type="number" min="1" value={String(config.NUMBER_OF_TUNERS || "")} onChange={(e) => set("NUMBER_OF_TUNERS", e.target.value)} /></label>
                    <label>Fonte EPG<select value={String(config.EPG_SOURCE || "XEPG")} onChange={(e) => set("EPG_SOURCE", e.target.value)}><option value="PMS">PMS</option><option value="XEPG">XEPG</option></select></label>
                    <label>Interface API<select value={String(config.API_INTERFACE_ENABLED || "1")} onChange={(e) => set("API_INTERFACE_ENABLED", e.target.value)}><option value="1">Ativada</option><option value="0">Desativada</option></select></label>
                    <label>Agenda de arquivos<input value={String(config.FILE_UPDATE_SCHEDULE || "")} onChange={(e) => set("FILE_UPDATE_SCHEDULE", e.target.value)} placeholder="0800,1200,1800" /></label>
                    <label>Atualizar arquivos ao iniciar<select value={String(config.UPDATE_FILES_ON_STARTUP || "0")} onChange={(e) => set("UPDATE_FILES_ON_STARTUP", e.target.value)}><option value="0">Não</option><option value="1">Sim</option></select></label>
                    <label>Local de arquivos temporários<input value={String(config.TEMP_FILES_LOCATION || "")} onChange={(e) => set("TEMP_FILES_LOCATION", e.target.value)} /></label>
                    <label>Cache de imagens XMLTV<select value={String(config.IMAGE_CACHING || "1")} onChange={(e) => set("IMAGE_CACHING", e.target.value)}><option value="1">Ativado</option><option value="0">Desativado</option></select></label>
                    <label>Substituir imagens ausentes<select value={String(config.REPLACE_MISSING_PROGRAM_IMAGES || "1")} onChange={(e) => set("REPLACE_MISSING_PROGRAM_IMAGES", e.target.value)}><option value="1">Ativado</option><option value="0">Desativado</option></select></label>
                    <label>Buffer de stream<select value={String(config.STREAM_BUFFER_ENABLED || "0")} onChange={(e) => set("STREAM_BUFFER_ENABLED", e.target.value)}><option value="0">Desativado</option><option value="1">Ativado</option></select></label>
                    <label>Endereço UDPxy<input value={String(config.UDPPROXY_ADDRESS || "")} onChange={(e) => set("UDPPROXY_ADDRESS", e.target.value)} /></label>
                    <label>Tamanho do buffer (MB)<input type="number" min="1" value={String(config.BUFFER_SIZE_MB || "")} onChange={(e) => set("BUFFER_SIZE_MB", e.target.value)} /></label>
                    <label>Timeout de cliente (ms)<input type="number" min="1" value={String(config.CLIENT_CONNECTION_TIMEOUT_MS || "")} onChange={(e) => set("CLIENT_CONNECTION_TIMEOUT_MS", e.target.value)} /></label>
                    <label>Caminho do FFmpeg<input value={String(config.FFMPEG_BINARY_PATH || "")} onChange={(e) => set("FFMPEG_BINARY_PATH", e.target.value)} /></label>
                    <label>Opções do FFmpeg<input value={String(config.FFMPEG_OPTIONS || "")} onChange={(e) => set("FFMPEG_OPTIONS", e.target.value)} /></label>
                    <label>Caminho do VLC/CVLC<input value={String(config.VLC_BINARY_PATH || "")} onChange={(e) => set("VLC_BINARY_PATH", e.target.value)} /></label>
                    <label>Opções do VLC/CVLC<input value={String(config.VLC_OPTIONS || "")} onChange={(e) => set("VLC_OPTIONS", e.target.value)} /></label>
                    <label>Local dos backups<input value={String(config.BACKUP_LOCATION || "")} onChange={(e) => set("BACKUP_LOCATION", e.target.value)} /></label>
                    <label>Backups mantidos<input type="number" min="1" value={String(config.BACKUPS_TO_KEEP || "")} onChange={(e) => set("BACKUPS_TO_KEEP", e.target.value)} /></label>
                    <label>Autenticação web<select value={String(config.WEB_AUTHENTICATION || "1")} onChange={(e) => set("WEB_AUTHENTICATION", e.target.value)}><option value="1">Ativada</option><option value="0">Desativada</option></select></label>
                </div>
                <label>
                    Links remotos M3U, separados por ;
                    <textarea
                        value={String(config.REMOTE_M3U_URLS || "")}
                        onChange={(e) => set("REMOTE_M3U_URLS", e.target.value)}
                    />
                </label>
                <label>
                    Links EPG XMLTV, separados por ;
                    <textarea
                        value={String(config.EPG_URLS || "")}
                        onChange={(e) => set("EPG_URLS", e.target.value)}
                    />
                </label>
                <div className="settings-test-card">
                    <PanelTitle kicker="CONECTIVIDADE" title="Teste de internet e ping" badge="TEMPO REAL" />
                    <div className="form-grid">
                        <label>Destino do teste (IP ou URL)
                            <input value={String(config.INTERNET_TEST_TARGET || "")} onChange={(e) => set("INTERNET_TEST_TARGET", e.target.value)} placeholder="https://1.1.1.1" />
                        </label>
                        <label>Delay entre testes (segundos)
                            <input type="number" min="1" value={String(config.INTERNET_PING_INTERVAL_SECONDS || "5")} onChange={(e) => set("INTERNET_PING_INTERVAL_SECONDS", e.target.value)} />
                        </label>
                        <label>Tempo máximo do ping (segundos)
                            <input type="number" min="0.2" step="0.1" value={String(config.INTERNET_PING_TIMEOUT_SECONDS || "2")} onChange={(e) => set("INTERNET_PING_TIMEOUT_SECONDS", e.target.value)} />
                        </label>
                    </div>
                    <InternetTestPreview
                        target={String(config.INTERNET_TEST_TARGET || "")}
                        intervalSeconds={Math.max(1, Number(config.INTERNET_PING_INTERVAL_SECONDS || 5))}
                    />
                </div>
                <button className="button primary" onClick={save}>
                    <Save size={15} />{" "}
                    {saved ? "Configurações salvas" : "Salvar configurações"}
                </button>
            </div>
        </>
    );
}

export function InternetTestPreview({ target, intervalSeconds }: { target: string; intervalSeconds: number }) {
    const [result, setResult] = useState<InternetHealth | null>(null);
    useEffect(() => {
        const run = () => api<InternetHealth>("/api/v1/internet-health").then(setResult).catch(() => setResult(null));
        run();
        const t = setInterval(run, intervalSeconds * 1000);
        return () => clearInterval(t);
    }, [target, intervalSeconds]);
    return (
        <div className={`internet-test-box ${result?.online ? "online" : result ? "offline" : "unknown"}`}>
            <div><span>Status</span><strong>{result?.online ? "ONLINE" : result ? "OFFLINE" : "VERIFICANDO"}</strong></div>
            <div><span>Ping</span><strong>{result ? `${result.latency_ms} ms` : "—"}</strong></div>
            <div><span>Destino</span><strong title={result?.target || target}>{result?.target || target || "—"}</strong></div>
            {result?.error && <small>{result.error}</small>}
        </div>
    );
}
