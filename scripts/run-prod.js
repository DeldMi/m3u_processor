const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

// O processo de produção sempre usa o virtualenv localizado na raiz do projeto.
// Isso evita referências a caminhos absolutos de outra máquina.
const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (!fs.existsSync(envPath)) {
        if (!fs.existsSync(examplePath)) {
            throw new Error('.env e .env.example não foram encontrados.');
        }
        fs.copyFileSync(examplePath, envPath);
        console.log('[OK] .env criado a partir do .env.example.');
    }
}

function pythonPath() {
    return isWin
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');
}

function start(module, extraEnv = {}) {
    const executable = pythonPath();
    if (!fs.existsSync(executable)) {
        throw new Error(`Python virtualenv não encontrado: ${executable}. Execute npm run setup.`);
    }
    return spawn(executable, ['-m', module], {
        cwd: rootDir,
        stdio: 'inherit',
        shell: false,
        env: { ...process.env, ...extraEnv },
    });
}

function main() {
    ensureEnvFile();

    const distIndex = path.join(rootDir, 'frontend', 'react', 'dist', 'index.html');
    if (!fs.existsSync(distIndex)) {
        throw new Error('Build do frontend ausente. Execute npm run build antes de npm run start.');
    }

    console.log('[INFO] Iniciando aplicação em produção...');
    const backend = start('src.app');
    const publicServer = start('src.public_server', { PUBLIC_ONLY: '1' });
    let stopping = false;

    const stop = (signal = 'SIGTERM') => {
        if (stopping) return;
        stopping = true;
        for (const child of [backend, publicServer]) {
            if (!child.killed) child.kill(signal);
        }
    };

    process.on('SIGINT', () => { stop(); process.exit(0); });
    process.on('SIGTERM', () => { stop(); process.exit(0); });

    backend.on('exit', (code) => {
        if (stopping) return;
        console.error(`[ERRO] Backend encerrou inesperadamente (código ${code ?? 0}).`);
        stop();
        process.exit(code || 1);
    });

    publicServer.on('exit', (code) => {
        if (stopping) return;
        console.error(`[ERRO] Servidor público encerrou inesperadamente (código ${code ?? 0}).`);
        stop();
        process.exit(code || 1);
    });
}

try {
    main();
} catch (error) {
    console.error(`[ERRO] ${error.message}`);
    process.exit(1);
}
