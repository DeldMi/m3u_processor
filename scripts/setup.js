const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

// Raiz absoluta do projeto. Nenhum caminho do computador do desenvolvedor
// deve ser gravado no projeto.
const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const dryRun = process.argv.includes('--dry-run');

function log(message) {
    console.log(message);
}

function fail(message) {
    throw new Error(message);
}

function run(command, args, options = {}) {
    log(`> ${command} ${args.join(' ')}`);
    if (dryRun) return { status: 0 };

    const result = spawnSync(command, args, {
        cwd: rootDir,
        stdio: 'inherit',
        shell: false,
        ...options,
    });

    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error(`Comando terminou com código ${result.status}: ${command}`);
    }

    return result;
}

function getNpmCommand() {
    // npm_execpath permite que o script funcione também quando chamado por
    // Corepack, npx ou outra instalação de npm que use um caminho explícito.
    const execPath = process.env.npm_execpath;
    if (execPath) {
        return { command: process.execPath, args: [execPath] };
    }
    return { command: isWin ? 'npm.cmd' : 'npm', args: [] };
}

function runNpm(args) {
    const npm = getNpmCommand();
    return run(npm.command, [...npm.args, ...args]);
}

function findCommand(candidates, args = ['--version']) {
    for (const candidate of candidates) {
        const result = spawnSync(candidate, args, {
            cwd: rootDir,
            stdio: 'ignore',
            shell: false,
        });
        if (!result.error && result.status === 0) return candidate;
    }
    return null;
}

function getSystemPython() {
    const candidates = isWin ? ['py', 'python'] : ['python3', 'python'];
    const python = findCommand(candidates);
    if (!python) {
        fail('Python 3 não encontrado. Instale Python 3.11+ e execute o setup novamente.');
    }
    return python;
}

function getVenvPython() {
    return isWin
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');
}

function ensureNode() {
    const node = findCommand(['node']);
    if (!node) fail('Node.js não encontrado. Instale Node.js 18+ antes de continuar.');
}

function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (fs.existsSync(envPath)) return;
    if (!fs.existsSync(examplePath)) {
        fail('Arquivo .env.example não encontrado; não foi possível criar o .env.');
    }
    fs.copyFileSync(examplePath, envPath);
    log('[OK] Arquivo .env criado a partir do .env.example.');
}

function ensureVenv(pythonCommand) {
    const venvPython = getVenvPython();
    if (!fs.existsSync(venvPython)) {
        log('[INFO] Criando ambiente virtual Python local...');
        run(pythonCommand, ['-m', 'venv', '.venv']);
    }
    if (!fs.existsSync(venvPython)) {
        fail(`Ambiente virtual não foi criado em ${venvPython}.`);
    }
    return venvPython;
}

function installPythonDeps(venvPython) {
    run(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip']);
    run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt']);
}

function installFrontendDeps() {
    const frontendDir = path.join(rootDir, 'frontend', 'react');
    const packageJson = path.join(frontendDir, 'package.json');
    const lockPath = path.join(frontendDir, 'package-lock.json');

    if (!fs.existsSync(packageJson)) {
        fail('frontend/react/package.json não encontrado.');
    }

    // npm ci só é usado quando existe lockfile. Caso contrário, npm install
    // cria o lockfile para que as próximas instalações sejam determinísticas.
    if (fs.existsSync(lockPath)) {
        runNpm(['--prefix', 'frontend/react', 'ci']);
    } else {
        runNpm(['--prefix', 'frontend/react', 'install']);
    }

    runNpm(['--prefix', 'frontend/react', 'run', 'build']);

    const distIndex = path.join(frontendDir, 'dist', 'index.html');
    if (!fs.existsSync(distIndex)) {
        fail('Build React terminou sem gerar frontend/react/dist/index.html.');
    }
}

function main() {
    log('=== M3U Processor - Setup ===');
    ensureNode();
    const systemPython = getSystemPython();
    ensureEnvFile();

    const venvPython = ensureVenv(systemPython);
    installPythonDeps(venvPython);
    installFrontendDeps();

    log('\n[OK] Ambiente configurado com sucesso.');
    log('[OK] Python virtualenv: .venv');
    log('[OK] Frontend: frontend/react/dist');
    log('[OK] Execute `npm run verify` para validar a instalação.');
    log('[OK] Execute `npm run dev` para desenvolvimento ou `npm run start` para produção.');
}

try {
    main();
} catch (error) {
    console.error(`\n[ERRO] ${error.message}`);
    process.exit(1);
}
