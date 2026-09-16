const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

function getNpmSpawnConfig(args, extraEnv = {}) {
    const execPath = process.env.npm_execpath;
    if (execPath) {
        return {
            command: process.execPath,
            args: [execPath, ...args],
        };
    }

    return {
        command: isWin ? 'npm.cmd' : 'npm',
        args,
    };
}

function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (!fs.existsSync(envPath) && fs.existsSync(examplePath)) {
        fs.copyFileSync(examplePath, envPath);
    }
}

function getVenvPython() {
    return isWin
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');
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
    const details = getNpmSpawnConfig(args, extraEnv);
    return spawnProcess(details.command, details.args, extraEnv);
}

function main() {
    ensureEnvFile();
    const venvPython = getVenvPython();

    if (!fs.existsSync(venvPython)) {
        console.log('[INFO] Ambiente ainda nao configurado. Rodando npm run setup...');
        const setup = spawnNpm(['run', 'setup']);
        setup.on('exit', (code) => {
            if (code !== 0) process.exit(code || 1);
            startServers();
        });
        return;
    }

    startServers();
}

function startServers() {
    console.log('[INFO] Iniciando backend e frontend em modo desenvolvimento...');
    const backend = spawnProcess(getVenvPython(), ['-m', 'src.app']);
    const publicServer = spawnProcess(getVenvPython(), ['-m', 'src.public_server'], { PUBLIC_ONLY: '1' });
    const frontend = spawnNpm(['--prefix', 'frontend/react', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', '5173']);

    const stop = (signal) => {
        backend.kill(signal);
        publicServer.kill(signal);
        frontend.kill(signal);
    };

    process.on('SIGINT', () => stop('SIGINT'));
    process.on('SIGTERM', () => stop('SIGTERM'));

    backend.on('exit', (code) => {
        console.log(`Backend encerrado com codigo ${code}`);
        frontend.kill('SIGTERM');
        publicServer.kill('SIGTERM');
        process.exit(code ?? 0);
    });

    frontend.on('exit', (code) => {
        console.log(`Frontend encerrado com codigo ${code}`);
        backend.kill('SIGTERM');
        publicServer.kill('SIGTERM');
        process.exit(code ?? 0);
    });
}

main();
