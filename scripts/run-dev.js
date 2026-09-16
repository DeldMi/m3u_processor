const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

function getVenvPython() {
    return isWin
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');
}

function getSystemCommand(name) {
    if (!isWin) return name;
    return name === 'npm' ? 'npm.cmd' : name;
}

function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (!fs.existsSync(envPath) && fs.existsSync(examplePath)) {
        fs.copyFileSync(examplePath, envPath);
        console.log('[OK] .env criado a partir do .env.example.');
    }
}

function isPythonHealthy(python) {
    if (!fs.existsSync(python)) return false;
    const result = spawnSync(python, ['-c', 'import sys; print(sys.executable)'], {
        cwd: rootDir,
        stdio: 'ignore',
        shell: false,
    });
    return !result.error && result.status === 0;
}

function hasFrontendDependencies() {
    const frontend = path.join(rootDir, 'frontend', 'react', 'node_modules');
    const binary = path.join(frontend, '.bin', isWin ? 'vite.cmd' : 'vite');
    const tsc = path.join(frontend, '.bin', isWin ? 'tsc.cmd' : 'tsc');
    return fs.existsSync(binary) && fs.existsSync(tsc);
}

function runSetup() {
    const result = isWin
        ? spawnSync(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', 'npm run setup'], {
            cwd: rootDir,
            stdio: 'inherit',
            shell: false,
            env: process.env,
        })
        : spawnSync('npm', ['run', 'setup'], {
            cwd: rootDir,
            stdio: 'inherit',
            shell: false,
            env: process.env,
        });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`Setup terminou com código ${result.status}.`);
}

function ensureSetup() {
    const python = getVenvPython();
    const distIndex = path.join(rootDir, 'frontend', 'react', 'dist', 'index.html');

    if (!isPythonHealthy(python) || !fs.existsSync(distIndex) || !hasFrontendDependencies()) {
        console.log('[INFO] Ambiente incompleto ou dependências do frontend ausentes. Executando npm run setup...');
        runSetup();
    }

    if (!isPythonHealthy(python)) throw new Error(`Python virtualenv inválido: ${python}`);
    if (!hasFrontendDependencies()) throw new Error('Dependências React ausentes. Execute `npm run setup`.');
    if (!fs.existsSync(distIndex)) throw new Error('Build React ausente: frontend/react/dist/index.html.');
}

function spawnProcess(command, args, extraEnv = {}) {
    return spawn(command, args, {
        cwd: rootDir,
        stdio: 'inherit',
        shell: false,
        env: { ...process.env, ...extraEnv },
    });
}

function spawnNpm(args) {
    if (!isWin) return spawnProcess('npm', args);

    return spawnProcess(
        process.env.ComSpec || 'cmd.exe',
        ['/d', '/s', '/c', ['npm', ...args.map((arg) => quoteCmdArg(String(arg)))].join(' ')],
    );
}

function quoteCmdArg(value) {
    if (/^[A-Za-z0-9_./:=@%+,-]+$/.test(value)) return value;
    return `"${value.replace(/"/g, '\\"')}"`;
}

function main() {
    ensureEnvFile();
    ensureSetup();
    startServers();
}

function startServers() {
    console.log('[INFO] Iniciando backend, servidor público e frontend...');
    const python = getVenvPython();

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

    const failIfUnexpectedExit = (name, code) => {
        if (stopping) return;
        console.error(`[ERRO] ${name} encerrou inesperadamente (código ${code ?? 0}).`);
        stop();
        process.exit(code || 1);
    };

    backend.on('error', (error) => {
        console.error(`[ERRO] Falha ao iniciar backend: ${error.message}`);
        stop();
        process.exit(1);
    });
    publicServer.on('error', (error) => {
        console.error(`[ERRO] Falha ao iniciar servidor público: ${error.message}`);
        stop();
        process.exit(1);
    });
    frontend.on('error', (error) => {
        console.error(`[ERRO] Falha ao iniciar frontend: ${error.message}`);
        stop();
        process.exit(1);
    });

    backend.on('exit', (code) => failIfUnexpectedExit('Backend', code));
    publicServer.on('exit', (code) => failIfUnexpectedExit('Servidor público', code));
    frontend.on('exit', (code) => failIfUnexpectedExit('Frontend', code));
}

try {
    main();
} catch (error) {
    console.error(`[ERRO] ${error.message}`);
    process.exit(1);
}
