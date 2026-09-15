# Sistema Automatizado de Saneamento e Agendamento M3U/M3U8

## Visão Geral
Solução técnica projetada para auditoria contínua e particionamento de listas multimídia. Suporta ingestão híbrida (arquivos locais na pasta `input/` e listas remotas via URL), particionando os fluxos operantes em lotes de no máximo 400 canais por arquivo, expurgando streams inoperantes e mantendo auditoria em JSON.

## Parâmetros do Arquivo `.env`
* `MAX_CHANNELS_PER_FILE`: Inteiro determinando a capacidade máxima de cada arquivo de saída (Padrão: 400).
* `CONCURRENCY_LIMIT`: Quantidade máxima de sockets assíncronos abertos em simultâneo (Padrão: 50).
* `REQUEST_TIMEOUT`: Limite de espera em segundos por requisição de canal (Padrão: 6).
* `REMOTE_M3U_URLS`: Lista de URLs separadas por ponto e vírgula (`;`).
* `SCHEDULE_MODE`: Política de execução do agendador:
  - `DISABLED`: Sem agendamento, apenas disparo manual.
  - `INTERVAL`: Repetição periódica em horas (ex: a cada 12 horas).
  - `CRON`: Execução em horário diário fixo de 24 horas (ex: `03:00` para 3h da manhã).

## Modos de Operação
1. **Configuração Inicial**: Execute `setup_env.bat` uma única vez para criar o ambiente isolado `.venv` e instalar os pacotes.
2. **Execução Automática / Dashboard**: Execute `run_menu.bat`. A aplicação abre a interface gráfica em `http://127.0.0.1:5000`. O agendador (*APScheduler*) fica residente em segundo plano executando os ciclos programados.
3. **Execução Pontual**: Execute `run_checker.bat` para rodar uma única auditoria direta via CLI (*Command Line Interface* / Interface de Linha de Comando).