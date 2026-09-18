# Acesso, recuperação e segurança

## Login padrão

O sistema provisiona um usuário administrador inicial assim que o banco é criado:

- usuário: `admin`
- senha: definida por `ADMIN_INITIAL_PASSWORD`; o `npm run setup` gera uma senha aleatória para instalações novas.

## Como acessar

Abra no navegador:

```text
http://127.0.0.1:5000
```

ou, se configurado em outro host/porta:

```text
http://SEU_IP:PORTA
```

## Como alterar a senha

O projeto não implementa recuperação por e-mail. A senha é armazenada no banco SQLite como hash.

### Método 1: criar outro usuário admin

1. faça login com a conta atual
2. vá para `Usuários`
3. crie um novo usuário com perfil `admin`
4. faça login com esse novo usuário
5. remova o usuário antigo se necessário

### Método 2: resetar via banco SQLite

#### Linux/macOS

```bash
python - <<'PY'
from werkzeug.security import generate_password_hash
import sqlite3
conn = sqlite3.connect('data/app.db')
cur = conn.cursor()
new_hash = generate_password_hash('nova_senha_segura')
cur.execute("UPDATE users SET password_hash = ? WHERE username = 'admin';", (new_hash,))
conn.commit()
conn.close()
print('Senha atualizada com sucesso.')
PY
```

Depois faça login com:

- usuário: `admin`
- senha: `nova_senha_segura`

#### Windows (PowerShell)

```powershell
python -c "from werkzeug.security import generate_password_hash; import sqlite3; conn=sqlite3.connect('data/app.db'); cur=conn.cursor(); cur.execute(\"UPDATE users SET password_hash = ? WHERE username = 'admin';\", (generate_password_hash('nova_senha_segura'),)); conn.commit(); conn.close(); print('Senha atualizada com sucesso.')"
```

## Como recuperar acesso se esquecer a senha

Sem e-mail ou MFA, o método recomendado é:

1. localizar o banco em `data/app.db`
2. alterar a senha do usuário `admin` com um script Python
3. reiniciar a aplicação

## Como identificar usuários existentes

```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect('data/app.db')
for row in conn.execute('SELECT id, username, role FROM users ORDER BY id'):
    print(row)
conn.close()
PY
```

## Permissões por papel

### `admin`

- alterar configurações gerais
- acessar usuários
- criar/editar usuários
- controlar agendamento
- alterar o endereço base do sistema

### `editor`

- editar canais
- gerar playlists
- iniciar/parar sincronização
- gerenciar listas publicadas

### `viewer`

- visualizar painel
- visualizar listas
- acessar reprodução de canais
- sem ações de alteração

## Como criar um usuário novo

No painel web:

- acesse `Usuários`
- preencha nome de usuário e senha
- escolha papel (`viewer`, `editor`, `admin`)
- salvar

## Como remover um usuário

O projeto atual não fornece um botão de exclusão explícito na UI. O caminho mais simples é:

```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect('data/app.db')
cur = conn.cursor()
cur.execute("DELETE FROM users WHERE username = 'usuario_que_quero_remover'")
conn.commit()
conn.close()
print('Usuário removido.')
PY
```

## Recomendação de segurança

- trocar a senha padrão imediatamente
- criar usuário administrativo dedicado
- usar `viewer` para usuários só de leitura
- habilitar HTTPS em produção
- proteger o arquivo `.env`
- manter `BASE_URL` correto

## Dica importante

A recuperação de senha por e-mail ainda não está implementada neste projeto. O sistema depende de acesso direto ao banco SQLite ou da criação de outra conta administrativa.

---

Documentação relacionada:

- [configuracao.md](configuracao.md)
- [troubleshooting.md](troubleshooting.md)
- [arquitetura.md](arquitetura.md)
