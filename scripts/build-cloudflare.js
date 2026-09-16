const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const FRONTEND = path.join(ROOT, 'frontend', 'react');
const DIST = path.join(FRONTEND, 'dist');
const isWindows = process.platform === 'win32';
const npmCommand = isWindows ? 'npm.cmd' : 'npm';

function run(command, args, label, cwd = ROOT) {
    console.log(`\n==> ${label}`);
    const result = spawnSync(command, args, {
        cwd,
        stdio: 'inherit',
        shell: false,
        env: {
            ...process.env,
            CF_PAGES: '1',
            CLOUDFLARE_PAGES: '1',
        },
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

if (!fs.existsSync(path.join(FRONTEND, 'package.json'))) {
    console.error('[ERRO] package.json do frontend não encontrado em frontend/react.');
    process.exit(1);
}

// Cloudflare Workers Builds/Pages pode instalar as dependências do diretório raiz
// usando Bun. O projeto, porém, possui uma aplicação React independente em
// frontend/react. Instale explicitamente as dependências dela antes do build.
const frontendNodeModules = path.join(FRONTEND, 'node_modules');
const frontendLock = path.join(FRONTEND, 'package-lock.json');

if (!fs.existsSync(frontendNodeModules)) {
    if (fs.existsSync(frontendLock)) {
        run(npmCommand, ['ci', '--no-audit', '--no-fund'], 'Instalar dependências do frontend', FRONTEND);
    } else {
        run(npmCommand, ['install', '--no-audit', '--no-fund'], 'Instalar dependências do frontend', FRONTEND);
    }
}

const tsc = path.join(
    frontendNodeModules,
    '.bin',
    isWindows ? 'tsc.cmd' : 'tsc',
);

if (!fs.existsSync(tsc)) {
    console.error('[ERRO] TypeScript não foi instalado corretamente em frontend/react/node_modules.');
    process.exit(1);
}

run(npmCommand, ['run', 'build'], 'Build Cloudflare Pages', FRONTEND);

if (!fs.existsSync(path.join(DIST, 'index.html'))) {
    console.error('[ERRO] O build Cloudflare não gerou frontend/react/dist/index.html.');
    process.exit(1);
}

console.log('\nBUILD CLOUDFLARE CONCLUÍDO.');
console.log(`Saída: ${DIST}`);
