# Troubleshooting e solução de problemas

## Problemas comuns

### 1. Erro: `ModuleNotFoundError`

Causa provável:

- dependências Python não instaladas
- ambiente virtual não ativado

Solução:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No Windows:

```bat
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 2. Erro: `npm: command not found`

Causa:

- Node.js não instalado ou não está no `PATH`

Solução:

Instalar Node.js LTS e reiniciar terminal.

### 3. O app não abre no navegador

Verifique:

- se o Flask está em execução
- se a porta 5000 não está ocupada
- se o build do React existe em `frontend/react/dist`

Comando para iniciar:

```bash
python -m src.app
```

Se quiser reiniciar em ambiente local:

```bash
./run_menu.sh
```

ou

```bat
run_menu.bat
```

### 4. Erro de acesso: login falha

Verifique:

- usuário e senha corretos
- se o banco SQLite foi criado em `data/app.db`
- se o `admin` ainda existe

Credencial inicial:

- usuário: `admin`
- senha: a senha aleatória exibida/criada pelo `npm run setup` em `ADMIN_INITIAL_PASSWORD` no `.env`

Se perdeu a senha ou o usuário foi removido, veja o guia de recuperação.

### 5. Portal fica em branco / frontend não renderiza

Solução:

```bash
cd frontend/react
npm install
npm run build
```

Depois reinicie o backend:

```bash
python -m src.app
```

### 6. Port 5000 já está em uso

Altere o `.env`:

```env
WEB_PORT=5001
BASE_URL=http://127.0.0.1:5001
```

Reinicie a aplicação.

### 7. O .env não existe

Crie a partir do exemplo:

```bash
cp exeplo.env .env
```

No Windows:

```bat
copy exeplo.env .env
```

### 8. O sistema não gera playlists

Verifique:

- `input/` contém arquivos válidos
- `REMOTE_M3U_URLS` está correto
- há canais válidos no banco
- `BASE_URL` está configurado corretamente

### 9. EPG/XML não aparece junto com M3U

Possíveis causas:

- `EPG_URLS` vazia ou inválida
- falha de rede ao baixar o XML
- problemas de permissão na pasta `output/`

### 10. O agendamento não dispara

Verifique:

```env
SCHEDULE_MODE='INTERVAL'
SCHEDULE_INTERVAL_HOURS=12
```

ou

```env
SCHEDULE_MODE='CRON'
SCHEDULE_CRON_TIME='03:00'
```

Depois reinicie o app.

### 11. Arquivos sensíveis apareceram no histórico do Git

O `.gitignore` impede novos arquivos de serem adicionados, mas não remove arquivos
que já foram versionados. Para conferir arquivos ignorados ainda rastreados:

```bash
git ls-files -ci --exclude-standard
```

Para parar de rastrear um arquivo sem apagá-lo localmente:

```bash
git rm --cached -- .env data/app.db
```

Se o arquivo já foi publicado em algum commit, é necessário reescrever o histórico
e fazer push forçado da branch. Antes disso, troque imediatamente senhas, tokens e
chaves que tenham sido expostos. O histórico antigo pode permanecer temporariamente
em caches internos do GitHub; para dados secretos, solicite a remoção ao suporte.

### 12. Erro `database or disk is full`

Esse erro significa que a unidade do projeto não consegue gravar no SQLite ou criar
arquivos temporários. Verifique o espaço livre, remova arquivos locais grandes ou
antigos e reinicie o backend. O sistema bloqueia novas sincronizações quando há
menos de 512 MB livres e evita iniciar várias sincronizações ao mesmo tempo.

## Log útil

Os relatórios de auditoria ficam em:

```text
logs/
```

Arquivos tipo:

```text
auditoria_20260915_105602.json
```

Esses arquivos ajudam a entender o que foi validado e quais canais foram considerados online/offline.

## Verificações rápidas

### Verificar se a estrutura existe

```bash
ls -la
ls -la input output logs data
```

### Verificar se o frontend foi compilado

```bash
ls -la frontend/react/dist
```

### Verificar se a aplicação está iniciada

```bash
ps -ef | grep python
```

## Reset limpo do ambiente

Quando necessário, pode resetar o ambiente local manualmente:

```bash
rm -rf .venv frontend/react/node_modules frontend/react/dist data/app.db
./setup_env.sh
```

No Windows:

```bat
rmdir /s /q .venv
rmdir /s /q frontend\react\node_modules
rmdir /s /q frontend\react\dist
del data\app.db
setup_env.bat
```

> Atenção: isso apaga o banco SQLite e os dados locais. Use com cautela.

---

Documentação relacionada:

- [instalacao.md](instalacao.md)
- [configuracao.md](configuracao.md)
- [acesso-e-recuperacao.md](acesso-e-recuperacao.md)
