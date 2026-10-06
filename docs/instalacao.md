# Instalação do projeto

## Requisitos mínimos

### Windows

- Windows 10/11
- Python 3.11+
- Node.js 20 ou 22 LTS
- npm
- Git (opcional, mas recomendado)

### Linux

- Ubuntu, Debian, Fedora, Alpine ou distro compatível
- Python 3.11+
- Node.js 20/22
- npm
- build-essential / gcc (se algum pacote compilável exigir)

### Docker

- Docker Engine
- Docker Compose

## Estrutura principal do repositório

```text
m3u_processor/
├── src/
├── frontend/
├── input/
├── output/
├── logs/
├── data/
├── .env
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── setup_env.sh
├── setup_env.bat
├── run_menu.sh
├── run_menu.bat
├── run_checker.sh
├── run_checker.bat
├── exeplo.env
├── README.md
└── docs/
```

## Instalação no Linux, macOS e Windows

### 1. Verificar requisitos

- Python 3.11 ou superior;
- Node.js 20/22 LTS;
- npm;
- Git somente para desenvolvimento e instalação a partir do repositório.

### 2. Criar o ambiente

Na raiz do projeto:

```bash
npm run setup
```

O setup:

- valida Node.js e Python;
- cria ou recria `.venv` quando necessário;
- instala `requirements.txt`;
- cria `.env` a partir de `exeplo.env` quando não existe;
- instala dependências com `npm ci` quando existe lockfile;
- executa o build React;
- valida `frontend/react/dist/index.html`.

O setup é idempotente e usa caminhos relativos. Não use caminhos absolutos da máquina.

### 3. Validar a instalação

```bash
npm run verify
```

### 4. Iniciar o ambiente local

```bash
npm run dev
```

Os serviços iniciam em:

```text
http://localhost:5173  # frontend Vite
http://localhost:5000  # Flask/API
http://localhost:8080  # servidor público de playlists/EPG
```

Os wrappers `setup_env.*` e `run_menu.*` continuam disponíveis por compatibilidade, mas não devem ser usados como fluxo oficial.

## Instalação via Docker

### 1. Ajustar variáveis de ambiente

Certifique-se de que exista um `.env` no diretório raiz.

### 2. Construir e subir o container

```bash
docker compose up -d --build
```

### 3. Verificar status

```bash
docker compose ps
```

### 4. Acessar

```text
http://localhost:5000
```

## Instalação manual (sem scripts)

### Instalando manualmente o ambiente Python

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# no Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend/react
npm ci
npm run build
```

Use `npm install` somente quando o projeto não possui `package-lock.json`.

### Rodar a aplicação

```bash
npm run dev
```

Para produção:

```bash
npm run build
npm run start
```

## Verificações pós-instalação

Confirme que os itens abaixo existam:

- `.env`
- `data/app.db`
- `frontend/react/dist/index.html`
- `output/`
- `logs/`
- `input/`

## Primeiro acesso

Credencial inicial:

- usuário: `admin`
- senha: a senha aleatória criada pelo setup e armazenada em `ADMIN_INITIAL_PASSWORD` no `.env`.

Se a base ainda estiver vazia, o sistema cria esse usuário automaticamente na primeira execução. A senha deve ser alterada no primeiro login.

## Como atualizar dependências

### Python

```bash
pip install -r requirements.txt
```

### Node

```bash
cd frontend/react
npm install
```

## Dicas de segurança

- nunca exponha o `.env` em repositório público
- mude a senha padrão após o primeiro login
- mantenha `BASE_URL` apontando para a URL pública correta
- em produção, use HTTPS e proxy reverso

---

Próximo passo:

- [configuracao.md](configuracao.md)
- [troubleshooting.md](troubleshooting.md)
- [acesso-e-recuperacao.md](acesso-e-recuperacao.md)
