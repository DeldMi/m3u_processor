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

## Instalação no Linux

### 1. Clonar ou abrir o projeto

```bash
cd /caminho/para/o/projeto
```

### 2. Preparar ambiente

```bash
chmod +x setup_env.sh run_menu.sh run_checker.sh
./setup_env.sh
```

Esse script:

- cria um `.venv`
- instala as dependências Python
- instala dependências do frontend
- executa `npm run build`
- cria `.env` se não existir

### 3. Iniciar a aplicação

```bash
./run_menu.sh
```

A aplicação será iniciada em:

```text
http://127.0.0.1:5000
```

## Instalação no Windows

### 1. Instalar dependências

- Python 3.11+
- Node.js LTS
- npm

### 2. Executar setup

```bat
setup_env.bat
```

### 3. Iniciar a aplicação

```bat
run_menu.bat
```

Isso abre o navegador para `http://127.0.0.1:5000` e inicia o Flask.

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
npm install
npm run build
```

### Rodar a aplicação

```bash
python -m src.app
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
- senha: a senha aleatória exibida/criada pelo `npm run setup` em `ADMIN_INITIAL_PASSWORD` no `.env`

Se a base ainda estiver vazia, o sistema cria esse usuário automaticamente na primeira execução.

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
