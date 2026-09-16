const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

function getNpmCommand() {
    const execPath = process.env.npm_execpath;
    if (execPath) return { command: process.execPath, prefix: [execPath] };
    return { command: isWin ? 'npm.cmd' : 'npm', prefix: [] };
}

function getVenvPython() {
    return isWin
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');
}

function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (!fs.existsSync(envPath) && fs.existsSync(examplePath)) {
        fs.copyFileSync(examplePath, envPath);
        console.log('[OK] .env criado a partir do .env.example.');
    }
}

function spawnProcess(command, args, extraEnv = {}) {
    return spawn(command, args, {
        cwd: rootDir,
        stdio: 'inherit',
        shell: false,
        env: { ...process.env, ...extraEnv },
    });
}

function spawnNpm(args, extraEnv = {}) {
    const npm = getNpmCommand();
    return spawnProcess(npm.command, [...npm.prefix, ...args], extraEnv);
}

function ensureSetup() {
    const python = getVenvPython();
    const distIndex = path.join(rootDir, 'frontend', 'react', 'dist', 'index.html');
    if (fs.existsSync(python) && fs.existsSync(distIndex)) return true;

    console.log('[INFO] Ambiente incompleto. Executando npm run setup...');
    const npm = getNpmCommand();
    const result = spawnSync(npm.command, [...npm.prefix, 'run', 'setup'], {
        cwd: rootDir,
        stdio: 'inherit',
        shell: false,
        env: process.env,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) {
        console.error(`[ERRO] Setup terminou com código ${result.status}.`);
        process.exit(result.status || 1);
    }
    return true;
}

function main() {
    ensureEnvFile();
    ensureSetup();
    startServers();
}

function startServers() {
    console.log('[INFO] Iniciando backend, servidor público e frontend...');
    const python = getVenvPython();
    if (!fs.existsSync(python)) {
        throw new Error(`Python virtualenv não encontrado: ${python}`);
    }

    const backend = spawnProcess(python, ['-m', 'src.app']);
    const publicServer = spawnProcess(python, ['-m', 'src.public_server'], { PUBLIC_ONLY: '1' });
    const frontend = spawnNpm([
        '--prefix', 'frontend/react', 'run', 'dev', '--',
        '--host', '0.0.0.0', '--port', '5173',
    ]);

    let stopping = false;
    const stop = (signal = 'SIGTERM') => {
        if (stopping) return;
        stopping = true;
        for (const child of [backend, publicServer, frontend]) {
            if (!child.killed) child.kill(signal);
        }
    };

    process.on('SIGINT', () => { stop(); process.exit(0); });
    process.on('SIGTERM', () => { stop(); process.exit(0); });

    const failIfUnexpectedExit = (name, child, code) => {
        if (stopping) return;
        console.error(`[ERRO] ${name} encerrou inesperadamente (código ${code ?? 0}).`);
        stop();
        process.exit(code || 1);
    };

    backend.on('exit', (code) => failIfUnexpectedExit('Backend', backend, code));
    publicServer.on('exit', (code) => failIfUnexpectedExit('Servidor público', publicServer, code));
    frontend.on('exit', (code) => failIfUnexpectedExit('Frontend', frontend, code));
}

try {
    main();
} catch (error) {
    console.error(`[ERRO] ${error.message}`);
    process.exit(1);
}
