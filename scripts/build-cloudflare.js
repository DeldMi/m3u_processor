const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const FRONTEND = path.join(ROOT, 'frontend', 'react');
const DIST = path.join(FRONTEND, 'dist');
const isWindows = process.platform === 'win32';
const npmCommand = isWindows ? 'npm.cmd' : 'npm';
const bunCommand = isWindows ? 'bun.exe' : 'bun';

function executableExists(command) {
    const result = spawnSync(command, ['--version'], {
        cwd: ROOT,
        stdio: 'ignore',
        shell: false,
        env: process.env,
    });
    return !result.error && result.status === 0;
}

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

function frontendTool(name) {
    return path.join(
        FRONTEND,
        'node_modules',
        '.bin',
        isWindows ? `${name}.cmd` : name,
    );
}

function rootTool(name) {
    return path.join(
        ROOT,
        'node_modules',
        '.bin',
        isWindows ? `${name}.cmd` : name,
    );
}

if (!fs.existsSync(path.join(FRONTEND, 'package.json'))) {
    console.error('[ERRO] package.json do frontend não encontrado em frontend/react.');
    process.exit(1);
}

const tsc = frontendTool('tsc');
const rootTsc = rootTool('tsc');
const hasBun = executableExists(bunCommand);

// Cloudflare Pages normalmente executa `bun install` antes do build. Bun pode
// hoistar as dependências no node_modules da raiz, sem criar
// frontend/react/node_modules. Nesse caso, não devemos iniciar um segundo
// gerenciador de pacotes com `npm ci`, pois o lockfile do npm pode não existir
// no ambiente efêmero do Pages.
if (!fs.existsSync(tsc) && !fs.existsSync(rootTsc)) {
    console.log('[INFO] Dependências do frontend não estão prontas. Instalando agora...');

    if (hasBun) {
        run(
            bunCommand,
            ['install'],
            'Instalar dependências com Bun',
            ROOT,
        );
    } else {
        run(
            npmCommand,
            ['install', '--no-audit', '--no-fund'],
            'Instalar dependências do frontend',
            FRONTEND,
        );
    }
}

const resolvedTsc = fs.existsSync(tsc) ? tsc : rootTsc;
if (!fs.existsSync(resolvedTsc)) {
    console.error('[ERRO] TypeScript não foi instalado corretamente.');
    process.exit(1);
}

// Se o ambiente já instalou com Bun, mantenha Bun como gerenciador do build.
// Caso contrário, use npm para instalações locais tradicionais.
if (hasBun) {
    run(bunCommand, ['run', 'build'], 'Build Cloudflare Pages', FRONTEND);
} else {
    run(npmCommand, ['run', 'build'], 'Build Cloudflare Pages', FRONTEND);
}

if (!fs.existsSync(path.join(DIST, 'index.html'))) {
    console.error('[ERRO] O build Cloudflare não gerou frontend/react/dist/index.html.');
    process.exit(1);
}

console.log('\nBUILD CLOUDFLARE CONCLUÍDO.');
console.log(`Saída: ${DIST}`);
