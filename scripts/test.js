const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

// Executa os testes Python com o mesmo ambiente usado pela aplicação.
const ROOT = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const python = isWin
    ? path.join(ROOT, '.venv', 'Scripts', 'python.exe')
    : path.join(ROOT, '.venv', 'bin', 'python');

if (!fs.existsSync(python)) {
    console.error('[ERRO] .venv não encontrado. Execute `npm run setup` primeiro.');
    process.exit(1);
}

const result = spawnSync(python, ['-m', 'unittest', 'discover', '-s', 'tests', '-v'], {
    cwd: ROOT,
    stdio: 'inherit',
    shell: false,
});

if (result.error) {
    console.error(`[ERRO] Falha ao executar testes: ${result.error.message}`);
    process.exit(1);
}

process.exit(result.status ?? 1);
