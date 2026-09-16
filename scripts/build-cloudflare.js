const { spawnSync } = require('node:child_process');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const isWindows = process.platform === 'win32';
const npmCommand = isWindows ? 'npm.cmd' : 'npm';

const result = spawnSync(
    npmCommand,
    ['--prefix', 'frontend/react', 'run', 'build'],
    {
        cwd: ROOT,
        stdio: 'inherit',
        shell: false,
        env: {
            ...process.env,
            CF_PAGES: '1',
            CLOUDFLARE_PAGES: '1',
        },
    },
);

if (result.error) {
    console.error(`[ERRO] Build Cloudflare: ${result.error.message}`);
    process.exit(1);
}

if (result.status !== 0) {
    console.error(`[ERRO] Build Cloudflare terminou com código ${result.status}`);
    process.exit(result.status ?? 1);
}

console.log('\nBUILD CLOUDFLARE CONCLUÍDO.');
console.log(`Saída: ${path.join(ROOT, 'frontend', 'react', 'dist')}`);
