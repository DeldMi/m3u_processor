# AGENTS.md

Contexto operacional do **M3U Processor / M3U Architect** para IAs, copilotos e colaboradores.

## Projeto

- Autor/titular declarado: **DeldMi**
- Licença: `LICENSE`
- Créditos: `NOTICE`
- Backend: Python + Flask
- Frontend: React + Vite + TypeScript + Tailwind + SCSS
- Banco: SQLite
- Agendamento: APScheduler
- Execução: Windows/Linux/macOS e Docker

Sistema para processar listas M3U/M3U8, validar canais, classificar metadados, gerar M3U/XMLTV em blocos, publicar arquivos e gerenciar usuários, permissões e configurações.

## Funcionalidades obrigatórias

### Painel Geral

- Indicador visual Internet **ONLINE/OFFLINE**.
- Latência em ms.
- Destino utilizado no teste.
- Saúde automática dos canais sem regenerar playlists.

### Canais e Editor

- Campo **CH. NO.** para editar o número do canal.
- Persistência no SQLite.
- Suporte a `tvg-chno` quando aplicável.
- Filtros por país, estado, cidade, categoria e status.
- Ordenação por cabeçalho.
- Seleção persistente de colunas.
- Upload local de logos.

### Configurações

- Destino do teste de Internet/ping.
- Intervalo/delay.
- Timeout.
- Resultado em tempo real.

### Playlists/EPG

- Nome personalizado na geração.
- Prefixo/arquivo customizado.
- Renomeação pareada de playlist e XMLTV.
- `BASE_URL` permanece a base pública global.
- Servidor público deve expor somente `/playlist/...` e `/epg/...`.

## Organização semântica

Backend:

- `src/app.py` — aplicação Flask e compatibilidade das rotas.
- `src/core/scheduler.py` — APScheduler.
- `src/domains/health/internet.py` — Internet/ping.
- `src/domains/playlists/service.py` — publicação/manifests.
- `src/domains/sync/service.py` — pipeline/sincronização/saúde.
- módulos legados (`manager.py`, `parser.py`, `checker.py`, `classifier.py`, `epg.py`) permanecem por compatibilidade.

Frontend:

- `frontend/react/src/app/App.tsx` — composição da SPA.
- `frontend/react/src/features/` — funcionalidades por domínio.
- `frontend/react/src/components/` — componentes compartilhados.
- `frontend/react/src/services/api.ts` — cliente HTTP.
- `frontend/react/src/types/` — contratos TypeScript.
- `frontend/react/src/main.tsx` — entrypoint.
- `frontend/react/src/styles.scss` — estilos globais.

Novas funcionalidades devem entrar no domínio correspondente; não aumentar `app.py` ou `main.tsx` com lógica de negócio.

## Instalação oficial

Na raiz do projeto:

```text
npm run setup
npm run verify
npm run dev
```

Produção:

```text
npm run setup
npm run build
npm run start
```

Docker:

```text
docker compose up -d --build
docker compose logs -f
docker compose down
```

### `npm run setup`

O setup é idempotente, cross-platform e não pode depender de caminhos absolutos da máquina.

1. verifica Node.js;
2. localiza Python 3 (`py -3`/`python` no Windows; `python3`/`python` em Unix);
3. cria `.venv` na raiz quando necessário;
4. verifica se o `.venv` realmente consegue iniciar o Python;
5. recria automaticamente um `.venv` inválido ou criado em outra pasta;
6. instala `requirements.txt` no `.venv`;
7. cria `.env` a partir de `.env.example` quando necessário;
8. usa `npm ci` se `frontend/react/package-lock.json` existir, caso contrário usa `npm install`;
9. executa o build React;
10. confirma `frontend/react/dist/index.html`.

**Não confiar somente na existência de `.venv/Scripts/python.exe`.** Um virtualenv pode ter sido criado em outro diretório e conservar referência ao Python antigo. O setup deve validar o executável antes de usá-lo.

O `setup.js` não pode chamar `main()` inexistente nem `installFrontendDeps()` recursivamente.

### Desenvolvimento

`npm run dev` usa sempre o Python de:

- Windows: `.venv\\Scripts\\python.exe`
- Linux/macOS: `.venv/bin/python`

O caminho é calculado relativo à raiz do projeto. Nunca usar caminhos como `C:\\www\\...` ou `/usr/bin/...`.

Antes de iniciar os processos, `run-dev.js` deve validar o `.venv` e o build. Se o ambiente estiver incompleto ou o virtualenv estiver inválido, executa o setup.

São iniciados backend Flask, servidor público e Vite. No Windows, `npm.cmd` deve ser iniciado de maneira compatível com `spawn`, evitando `EINVAL`.

### Produção

`npm run start` valida `.venv` e `frontend/react/dist/index.html` antes de iniciar backend e servidor público.

## Validação

- `npm run test` — executa os testes Python usando o `.venv` do projeto.
- `npm run typecheck` — executa o build TypeScript/Vite através de script cross-platform.
- `npm run build` — build TypeScript/Vite.
- `npm run verify` — sintaxe Python, testes, build React e arquivos obrigatórios.

Os scripts de validação não devem executar os testes com o Python global quando `.venv` estiver disponível, pois isso causa falsos erros como `ModuleNotFoundError: dotenv`.

No Windows, chamadas a `npm.cmd` devem usar `shell: true` quando iniciadas diretamente por `spawn`/`spawnSync`, evitando `spawnSync npm.cmd EINVAL`.

## Ambiente

Variáveis principais:

- `BASE_URL`
- `PUBLIC_BASE_URL`
- `WEB_HOST`
- `WEB_PORT`
- `PUBLIC_HOST`
- `PUBLIC_PORT`
- `MAX_CHANNELS_PER_FILE`
- `CONCURRENCY_LIMIT`
- `REQUEST_TIMEOUT`
- `USER_AGENT`
- `REMOTE_M3U_URLS`
- `SCHEDULE_MODE`
- `SCHEDULE_INTERVAL_HOURS`
- `SCHEDULE_CRON_TIME`
- `HEALTH_CHECK_INTERVAL_SECONDS`
- `API_TOKEN`
- `SECRET_KEY`

## Autenticação

Banco novo cria, conforme a documentação atual:

- `admin / admin123`

Roles:

- `admin` — administração, usuários e configurações.
- `editor` — canais, sincronização e geração.
- `viewer` — leitura/consumo.

## Compatibilidade e segurança

- Não remover endpoints existentes sem migração documentada.
- Preservar Flask + React + SQLite + scripts de raiz.
- Preservar `LICENSE`, `NOTICE` e créditos de DeldMi.
- Componentes de terceiros mantêm suas licenças/créditos.
- `.env`, bancos SQLite, logs, `output`, `dist`, `node_modules`, `.venv` e caches Python não devem entrar no Git.
- Nunca gravar caminhos absolutos da máquina nos scripts.
- O servidor público não pode expor menu ou APIs.

## Histórico Git

O histórico remoto foi limpo em 2026-09-15. Se um segredo voltar a ser publicado, revogar/trocar o segredo primeiro e somente depois limpar o histórico.

```bash
git ls-files -ci --exclude-standard
git rm --cached -- caminho/do/arquivo
```

## Problemas corrigidos nesta versão

- `npm ci` sem lockfile: o setup usa `npm ci` quando há lockfile e `npm install` quando não há.
- `main is not defined`: corrigido em `scripts/setup.js`.
- Recursão de `installFrontendDeps()`: removida.
- `/usr/bin\\python.exe`: não é mais usado pelo projeto.
- `.venv` em outro diretório: o setup detecta virtualenv inválido e recria o ambiente local.
- `ModuleNotFoundError: dotenv` nos testes: `verify` e `npm test` usam o Python do `.venv`.
- `spawnSync npm.cmd EINVAL`: scripts de npm no Windows usam execução compatível com `.cmd`.
- `run-dev.js`: valida/repara o ambiente antes de iniciar e não aceita um `.venv` quebrado apenas porque o arquivo existe.
- `run-prod.js`: valida ambiente e encerra processos irmãos de forma controlada.

## Recuperação de ambiente Windows

Se um projeto tiver sido movido de uma pasta para outra, por exemplo de `C:\\www\\m3u_processor` para outra unidade, o `.venv` antigo pode continuar apontando internamente para o Python da instalação anterior. **Não copiar `.venv` entre máquinas ou diretórios.**

A ação oficial é:

```text
npm run setup
```

O próprio setup deve detectar e recriar o ambiente virtual. Não é necessário alterar scripts para apontar para `/usr/bin/python.exe` ou para um caminho absoluto do computador.

## Prioridades

1. Instalação reproduzível.
2. Execução confiável em Windows e Linux.
3. Compatibilidade Flask/React.
4. Segurança e preservação de segredos.
5. UI coerente e funcional.
6. Playlists/EPG com nome personalizado.
7. Monitoramento de Internet e canais.
8. Organização semântica e documentação atualizada.
