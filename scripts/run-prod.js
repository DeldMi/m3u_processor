const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (!fs.existsSync(envPath) && fs.existsSync(examplePath)) fs.copyFileSync(examplePath, envPath);
}

function pythonPath() {
    return isWin ? path.join(rootDir, '.venv', 'Scripts', 'python.exe') : path.join(rootDir, '.venv', 'bin', 'python');
}

function start(module, extraEnv = {}) {
    return spawn(pythonPath(), ['-m', module], { cwd: rootDir, stdio: 'inherit', shell: false, env: { ...process.env, ...extraEnv } });
}

function main() {
    ensureEnvFile();
    const backend = start('src.app');
    const publicServer = start('src.public_server', { PUBLIC_ONLY: '1' });
    const stop = () => { backend.kill(); publicServer.kill(); };
    process.on('SIGINT', stop);
    process.on('SIGTERM', stop);
    backend.on('exit', code => { publicServer.kill(); process.exit(code ?? 0); });
}

main();
