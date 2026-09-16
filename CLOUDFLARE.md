# Cloudflare Pages — M3U Processor

## Arquitetura suportada

O projeto possui dois lados:

1. **Frontend React/Vite**: pode ser publicado no Cloudflare Pages.
2. **Backend Flask/Python**: continua sendo executado em um servidor/contêiner com Python e armazenamento persistente.

O Pages Functions deste repositório funciona como proxy para o backend através da variável `BACKEND_ORIGIN`. Assim, a SPA pode usar as mesmas URLs relativas (`/api`, `/login`, `/playlist`, `/epg`) tanto localmente quanto em produção.

> O Cloudflare Pages não executa automaticamente o servidor Flask deste projeto apenas por receber o diretório `dist`. O backend possui SQLite, APScheduler, processamento de M3U/EPG e filesystem persistente; por isso o deployment recomendado mantém o backend em um ambiente Python/Docker e usa Pages para a camada web.

## Build completo

Na raiz do projeto:

```bash
npm run setup
npm run build
```

`npm run build` não é apenas o build do React. Ele:

- compila o frontend React/TypeScript;
- valida/compila os módulos Python;
- cria `build/m3u-processor/` com o projeto executável;
- inclui frontend compilado, backend, scripts, testes, Docker e configurações;
- cria `build/m3u-processor-build.zip`;
- exclui `.env`, banco, logs, `input`, `output`, `node_modules`, `.venv` e caches.

Para somente o frontend:

```bash
npm run build:frontend
```

## Cloudflare Pages pelo GitHub — fluxo recomendado

Para este repositório, prefira **Git integration** no Cloudflare Pages. Nesse modo, o próprio Pages faz o build e publica o resultado após cada push na branch configurada.

No Cloudflare Dashboard, crie um projeto **Workers & Pages / Pages** e importe o repositório GitHub `DeldMi/m3u_processor`.

Configuração:

- Production branch: `main`
- Root directory: `/`
- Build command: `npm run build:cloudflare`
- Build output directory: `frontend/react/dist`
- Node.js: versão 22 ou superior
- **Deploy command: deixe vazio**

Não coloque `npx wrangler pages deploy ...` no comando de build/deploy de um projeto Pages conectado ao GitHub. O Pages já publica o diretório de saída quando o build termina.

### Se o projeto Pages ainda não existir

Crie-o pelo fluxo **Pages → Import an existing Git repository** e selecione este repositório. Não é necessário criar o projeto primeiro com `wrangler pages project create` quando a intenção é usar Git integration.

> Um projeto criado para Direct Upload/Wrangler segue um fluxo diferente. Não misture os dois métodos sem necessidade.

### Variável obrigatória do Pages

Em **Settings → Variables and Secrets**, configure:

```text
BACKEND_ORIGIN=https://backend.seu-dominio.com
```

Use somente a origem, sem `/api` no final. Exemplo:

```text
BACKEND_ORIGIN=https://m3u-backend.exemplo.com
```

A Function encaminha `/api/*`, `/login`, `/logout`, `/playlist/*` e `/epg/*` para essa origem. Arquivos estáticos continuam sendo servidos pelo Pages.

## Deploy manual via Wrangler — Direct Upload

Este é um fluxo alternativo, útil quando você deliberadamente quer fazer **Direct Upload**. O script do projeto para isso é separado do fluxo Git:

```bash
npm run build:cloudflare
npm run deploy:cloudflare:direct
```

O comando direto equivale a:

```bash
npx wrangler pages deploy frontend/react/dist --project-name m3u-processor
```

Se o projeto Direct Upload ainda não existir, crie-o primeiro com Wrangler. Não faça isso apenas para resolver um projeto que deveria usar Git integration.

## Backend

O backend pode ser executado por Docker:

```bash
docker compose up --build -d
```

Ou pelo ambiente Python local:

```bash
npm run setup
npm start
```

O backend deve estar acessível publicamente para o Pages, preferencialmente atrás de HTTPS. O domínio do frontend pode ser configurado como `BASE_URL`/`PUBLIC_BASE_URL` conforme o uso da aplicação.

## Desenvolvimento local do Pages Functions

```bash
npx wrangler pages dev frontend/react/dist --binding=BACKEND_ORIGIN:http://127.0.0.1:5000
```

## Observação sobre migração integral para Cloudflare

Existe suporte atual a Python Workers no Cloudflare, mas o runtime Python possui diferenças e limitações em relação a um ambiente CPython tradicional. Este projeto usa Flask, APScheduler, SQLite e operações de filesystem/processamento que precisam ser validadas antes de uma migração integral para Workers.

Portanto, a primeira etapa segura é **Pages + Functions proxy + backend Python persistente**. Uma migração integral para Workers/D1/R2 pode ser feita posteriormente como uma arquitetura específica, sem quebrar a instalação Docker/local existente.
