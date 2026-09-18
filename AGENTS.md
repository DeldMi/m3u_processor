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

Sistema para processar listas M3U/M3U8, validar canais, classificar metadados, gerar M3U/XMLTV em blocos, publicar arquivos e gerenciar usuários, permissões, configurações, manutenção e monitoramento.

## Regras de continuidade funcional

1. **Nenhuma funcionalidade existente deve ser removida sem solicitação explícita.** Ela pode ser remanejada para organização semântica, design ou requisitos de programação, mas o comportamento equivalente deve continuar disponível.
2. A base do projeto é **analisar, testar, processar e gerar links**, com administração completa: análise, teste, edição, criação, publicação e manutenção.
3. Correções devem priorizar integridade de dados, segurança, compatibilidade e funcionamento antes de refatorações estéticas.
4. Backend é a fonte de verdade para autorização. Ocultar controles no frontend não substitui autorização da API.

## Funcionalidades obrigatórias

### Painel Geral
- Internet ONLINE/OFFLINE, latência e destino do teste.
- Saúde automática dos canais sem regenerar playlists.
- Métricas e cards respeitam RBAC.

### Canais e Editor
- CH. NO. persistido no SQLite e compatível com `tvg-chno`.
- Filtros por país, estado, cidade, categoria e status.
- Ordenação por cabeçalho e seleção persistente de colunas.
- Upload local de logos.
- Visualizar, editar, criar, excluir e status protegidos individualmente.
- Usuário sem permissão de edição não pode executar a operação pela API.
- Canais OFFLINE **não são apagados automaticamente** durante saúde/sincronização. Exclusão persistida é ação explícita.

### Playlists/EPG
- Nome, prefixo e arquivo customizáveis.
- Renomeação pareada M3U/XMLTV.
- `BASE_URL` permanece base pública global.
- Servidor público expõe somente `/playlist/...` e `/epg/...`.
- Criar, regenerar, excluir, baixar/visualizar e administrar respeitam permissões.

## RBAC granular

Ações: `view`, `create`, `edit`, `delete`, `execute`, `admin`.

Recursos: dashboard, channels, playlists, epg, sync, health, settings, users, logs, maintenance, public_files e system.

A UI deve apresentar matriz Recurso × Ação e explicar o alcance de cada permissão. O backend deve rejeitar diretamente requisições não autorizadas com `403`.

`/api/me` retorna somente dados públicos necessários à interface; nunca senha, hash, token ou segredo.

## Segurança

- TLS verificado por padrão; certificados inválidos somente com `ALLOW_INSECURE_TLS=1`.
- Novas instalações não usam senha fixa pública. `npm run setup` gera `ADMIN_INITIAL_PASSWORD` aleatória quando necessário.
- `SECRET_KEY`, `API_TOKEN` e `ADMIN_INITIAL_PASSWORD` são segredos e nunca devem aparecer na API pública.
- Logs devem redigir credenciais presentes em URLs.
- Uploads devem validar extensão, nome seguro e diretório permitido.
- Arquivos públicos aceitam somente nomes/formatos permitidos.
- Nunca executar exclusões arbitrárias derivadas diretamente de entrada do usuário.

## Limpeza e manutenção

A manutenção deve ser seletiva, administrativa e limitada a diretórios conhecidos: cache, temporários, saída e logs. Nunca apagar banco, `.env`, configuração essencial ou caminho fora da raiz permitida. Operações destrutivas exigem confirmação e auditoria.

## Tutoriais e ajuda

Configurações, usuários, canais, playlists/EPG e Internet/Saúde devem possuir ajuda contextual explicando o que é, finalidade, funcionamento, configuração, impacto, exemplo, cuidados e restauração quando aplicável.

## Organização semântica

Backend: `src/app.py` para compatibilidade/rotas; `src/domains/` para regras de domínio; `src/domains/authz/` para identidade/RBAC; `src/domains/maintenance/` para manutenção; `src/domains/sync/` para pipeline; módulos legados permanecem por compatibilidade.

Frontend: `frontend/react/src/app/` composição; `features/` por domínio; `components/` compartilhados; `services/api.ts` HTTP; `types/` contratos.

Não aumentar `app.py` ou `main.tsx` com nova lógica de negócio quando existir domínio apropriado.

## Instalação oficial

Na raiz:

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

`npm run setup` deve ser idempotente e cross-platform, validar Node/Python, recriar `.venv` inválido, instalar `requirements.txt`, criar `.env`, instalar frontend usando `npm ci` quando houver lockfile e executar o build.

## Validação

- `npm run test` — testes Python no `.venv`.
- `npm run typecheck` — TypeScript/Vite.
- `npm run build` — frontend.
- `npm run verify` — sintaxe Python, testes, build e arquivos obrigatórios.

No Windows, `npm.cmd` deve ser executado de forma compatível com `spawn`.

## Correções críticas registradas — 2026-09-17

- preservação de canais offline;
- RBAC granular por recurso/ação;
- proteção de segredos;
- TLS seguro por padrão;
- senha administrativa inicial aleatória;
- compatibilidade `/assets` e `/app-assets`;
- parser M3U com metadados IPTV;
- tratamento estruturado de erros HTTP no frontend;
- pipeline de publicação com preservação da saída anterior;
- domínio semântico de manutenção;
- verificação cross-platform;
- testes de regressão para parser, RBAC e segurança.
