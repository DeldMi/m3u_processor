const { spawnSync } = require('node:child_process');
const path = require('node:path');

// O npm.cmd precisa ser executado via shell no Windows para evitar EINVAL.
const ROOT = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const npm = isWin ? 'npm.cmd' : 'npm';

const result = spawnSync(npm, ['--prefix', 'frontend/react', 'run', 'build'], {
    cwd: ROOT,
    stdio: 'inherit',
    shell: isWin,
    env: process.env,
});

if (result.error) {
    console.error(`[ERRO] Falha no typecheck/build: ${result.error.message}`);
    process.exit(1);
}

process.exit(result.status ?? 1);
