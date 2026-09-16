const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const isWindows = process.platform === 'win32';
const DIST = path.join(ROOT, 'frontend', 'react', 'dist');

function quoteCmdArg(value) {
    if (/^[A-Za-z0-9_./:=@%+,-]+$/.test(value)) return value;
    return `"${value.replace(/"/g, '\\"')}"`;
}

function runNpm(args, label) {
    console.log(`\n==> ${label}`);
    const result = isWindows
        ? spawnSync(process.env.ComSpec || 'cmd.exe', [
            '/d', '/s', '/c',
            ['npm', ...args.map((arg) => quoteCmdArg(String(arg)))].join(' '),
        ], {
            cwd: ROOT,
            stdio: 'inherit',
            shell: false,
            env: { ...process.env, CF_PAGES: '1', CLOUDFLARE_PAGES: '1' },
        })
        : spawnSync('npm', args, {
            cwd: ROOT,
            stdio: 'inherit',
            shell: false,
            env: { ...process.env, CF_PAGES: '1', CLOUDFLARE_PAGES: '1' },
        });

    if (result.error) {
        console.error(`[ERRO] ${label}: ${result.error.message}`);
        process.exit(1);
    }
    if (result.status !== 0) {
        console.error(`[ERRO] ${label} terminou com código ${result.status}`);
        process.exit(result.status ?? 1);
    }
}

const tsc = path.join(ROOT, 'frontend', 'react', 'node_modules', '.bin', isWindows ? 'tsc.cmd' : 'tsc');
if (!fs.existsSync(tsc)) {
    console.error('[ERRO] Dependências do frontend incompletas: TypeScript não encontrado. Execute `npm run setup`.');
    process.exit(1);
}

runNpm(['--prefix', 'frontend/react', 'run', 'build'], 'Build Cloudflare Pages');

if (!fs.existsSync(path.join(DIST, 'index.html'))) {
    console.error('[ERRO] O build Cloudflare não gerou frontend/react/dist/index.html.');
    process.exit(1);
}

console.log('\nBUILD CLOUDFLARE CONCLUÍDO.');
console.log(`Saída: ${DIST}`);
