m3u_processor/
│
├── Dockerfile                  # Construção da imagem Docker baseada em Linux Alpine/Slim
├── docker-compose.yml          # Orquestração do contêiner, mapeamento de portas e volumes
├── .env                        # Variáveis de ambiente, credenciais e parâmetros de rede
├── .env.example                # Modelo de referência das chaves de ambiente
├── .gitignore                  # Regras de exclusão para o versionamento Git
├── requirements.txt            # Dependências padronizadas do ecossistema Python
├── README.md                   # Documentação de engenharia de software e operação
│
├── setup_env.bat               # Instalação Windows
├── run_checker.bat             # Execução CLI Windows
├── run_menu.bat                # Painel Web Windows
│
├── setup_env.sh                # Instalação Linux/macOS
├── run_checker.sh              # Execução CLI Linux/macOS
├── run_menu.sh                 # Painel Web Linux/macOS
│
├── input/                      # Armazenamento de arquivos de entrada (.m3u, .m3u8, .txt)
├── output/                     # Listas e XMLTV fatiados em blocos de até 400 canais
├── logs/                       # Histórico estruturado de auditoria em formato JSON
├── data/                       # Banco de dados relacional SQLite (persistência de estado)
│
├── frontend/                   # Camada de Apresentação (Frontend desacoplado)
│   ├── templates/
│   │   ├── base.html           # Layout mestre responsivo com barra de navegação e submenus
│   │   ├── login.html          # Interface de autenticação com tratamento de sessão
│   │   ├── dashboard.html      # Métricas de execução, status do sistema e atalho de sincronização
│   │   ├── channels.html       # Visualizador/editor com filtros por País/Estado/Cidade/Tipo e Player HLS
│   │   ├── users.html          # Painel de provisionamento e permissões de usuários (RBAC)
│   │   └── settings.html       # Configurações de rede, agendador, chaves de API e Webhooks
│   └── static/
│       ├── css/
│       │   └── style.css       # Estilização visual (modo escuro de alta densidade informativa)
│       └── js/
│           ├── app.js          # Lógica assíncrona, chamadas fetch e reatividade
│           └── player.js       # Player HLS embutido (Hls.js / Video HTML5)
│
└── src/                        # Camada de Domínio e Infraestrutura (Backend)
    ├── __init__.py
    ├── db.py                   # Esquema SQLite relacional, transações e sanitização SQL
    ├── auth.py                 # Funções criptográficas de hashing (PBKDF2) e controle RBAC
    ├── config.py               # Manipulação e persistência transacional do arquivo .env
    ├── classifier.py           # Heurísticas de detecção de País, Estado, Cidade e VOD/Rádio
    ├── parser.py               # Extrator de metadados de listas IPTV
    ├── checker.py              # Sonda de rede assíncrona (Stream Probing) com bypass SSL
    ├── epg.py                  # Descompressão e particionamento de guia XMLTV
    ├── manager.py              # Orquestrador de deduplicação, expurgo e partições de 400 canais
    └── app.py                  # Servidor Flask, rotas de API RESTful e agendador APScheduler