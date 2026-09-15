# Processador, Auditor e Classificador M3U / IPTV

## Visão Geral da Arquitetura
Sistema estruturado para classificação taxonômica (País, Estado, Cidade), identificação de tipos de fluxo (Linear vs VOD/Rádio), expurgo de canais mortos e fatiamento estrito em blocos de até **400 canais por arquivo M3U e XMLTV**.

## Padrões de Segurança e Controle de Acesso (RBAC)
* `admin`: Acesso irrestrito a configurações de rede, credenciais e agendamentos.
* `editor`: Permissão para editar metadados, forçar status online/offline e disparar sincronizações.
* `viewer`: Restrito à navegação, reprodução de fluxos e consumo de links das listas geradas.

Credencial Padrão Inicial:
* **Usuário**: `admin`
* **Senha**: `admin123`

## Integração via API e Webhooks
Disparo de auditoria externa via requisição HTTP:
```bash
curl -X POST [http://127.0.0.1:5000/api/v1/sync](http://127.0.0.1:5000/api/v1/sync) \
     -H "Authorization: Bearer m3u_sec_token_99812401824"
```
Instruções de Implantação
Via Docker (Ambiente Isolado)

```sh
docker compose up -d --build
```

Acesse no navegador: http://localhost:5000
Opção 2: Local no Windows

    Execute ``` setup_env.bat ``` (uma vez).

    Execute ``` run_menu.bat ``` (abre o painel e agendador).

Opção 3: Local no Linux

```bash
chmod +x *.sh
./setup_env.sh
./run_menu.sh
```

---

```xml
 <FollowUp label="Quer suporte a múltiplos arquivos EPG simultâneos por país ou categoria?" query="Como configurar a mesclagem automática de múltiplos guias EPG de países diferentes do iptv-epg.org em cada partição de 400 canais?"/>
 ```

 # Procedimento de Inicialização

1.    Certifique-se de que os 4 arquivos acima estejam gravados dentro de C:\www\m3u_processor\frontend\templates\.

    2. Reinicie o servidor executando run_menu.bat.

    3. Acesse [http://127.0.0.1:5000](http://127.0.0.1:5000) no navegador.

    4. Efetue o login inicial com as credenciais padrão do banco:

        * Usuário: admin

        * Senha: admin123