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

function frontendTool(name) {
    return path.join(
        FRONTEND,
        'node_modules',
        '.bin',
        isWindows ? `${name}.cmd` : name,
    );
}

if (!fs.existsSync(path.join(FRONTEND, 'package.json'))) {
    console.error('[ERRO] package.json do frontend não encontrado em frontend/react.');
    process.exit(1);
}

// Cloudflare pode executar `bun install` na raiz antes deste script. Mesmo com
// o workspace declarado, a plataforma pode não materializar as dependências
// no diretório esperado pelo npm. Por isso, a presença real do TypeScript é a
// condição de prontidão do frontend.
const tsc = frontendTool('tsc');

if (!fs.existsSync(tsc)) {
    console.log('[INFO] Dependências do frontend não estão prontas. Instalando agora...');

    // Use `npm install`, e não `npm ci`, como fallback de build. O ambiente do
    // Cloudflare pode remover/ignorar lockfiles durante a etapa automática de
    // instalação (especialmente quando Bun é o gerenciador detectado). `npm
    // install` funciona tanto com quanto sem package-lock.json.
    run(
        npmCommand,
        ['install', '--no-audit', '--no-fund'],
        'Instalar dependências do frontend',
        FRONTEND,
    );
}

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
