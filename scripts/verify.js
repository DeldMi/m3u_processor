/**
 * Verificador oficial do projeto.
 *
 * O verificador sempre prefere o ambiente virtual localizado na raiz do
 * projeto. Isso evita executar os testes com um Python global sem Flask,
 * python-dotenv ou as demais dependências declaradas.
 */
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const isWindows = process.platform === 'win32';
const venvPython = isWindows
    ? path.join(ROOT, '.venv', 'Scripts', 'python.exe')
    : path.join(ROOT, '.venv', 'bin', 'python');
const pythonCandidates = isWindows ? [venvPython, 'py', 'python'] : [venvPython, 'python3', 'python'];

function run(command, args, label, options = {}) {
    console.log(`\n==> ${label}`);

    // No Windows, npm é um script .cmd. Executá-lo diretamente com shell:false
    // evita problemas de quoting/escaping do `cmd /c` e mantém a execução segura.
    const executable = isWindows && command === 'npm' ? 'npm.cmd' : command;
    const result = spawnSync(executable, args, {
        cwd: ROOT,
        stdio: 'inherit',
        shell: false,
        env: { ...process.env, ...(options.env || {}) },
    });

    if (result.error) {
        console.error(`Falha ao executar ${command}: ${result.error.message}`);
        return false;
    }
    if (result.status !== 0) {
        console.error(`${label} terminou com código ${result.status}.`);
        return false;
    }
    return true;
}

function findPython() {
    for (const candidate of pythonCandidates) {
        if (path.isAbsolute(candidate) && !fs.existsSync(candidate)) continue;
        const result = spawnSync(candidate, ['--version'], {
            cwd: ROOT,
            stdio: 'ignore',
            shell: false,
        });
        if (!result.error && result.status === 0) return candidate;
    }
    return null;
}

let ok = true;
const python = findPython();

if (!python) {
    console.error('Python não encontrado. Execute `npm run setup` primeiro.');
    ok = false;
} else {
    ok = run(python, ['-m', 'compileall', '-q', 'src'], 'Sintaxe Python') && ok;
    ok = run(python, ['-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'Testes Python') && ok;
}

const frontendDir = path.join(ROOT, 'frontend', 'react');
const frontendModules = path.join(frontendDir, 'node_modules');

if (!fs.existsSync(frontendModules)) {
    console.error('Dependências do frontend não encontradas. Execute `npm run setup` primeiro.');
    ok = false;
} else {
    ok = run(
        'npm',
        ['--prefix', 'frontend/react', 'run', 'build'],
        'Build React/TypeScript',
    ) && ok;
}

for (const required of [
    'AGENTS.md',
    'LICENSE',
    'NOTICE',
    'package.json',
    'frontend/react/src/main.tsx',
]) {
    if (!fs.existsSync(path.join(ROOT, required))) {
        console.error(`Arquivo obrigatório ausente: ${required}`);
        ok = false;
    }
}

console.log(`\n${ok ? 'VERIFICAÇÃO CONCLUÍDA COM SUCESSO.' : 'VERIFICAÇÃO ENCONTROU FALHAS.'}`);
process.exitCode = ok ? 0 : 1;
