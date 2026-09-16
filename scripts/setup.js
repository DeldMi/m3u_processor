const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

// A raiz é sempre calculada a partir do próprio script. Isso evita caminhos
// absolutos gravados no projeto e permite mover o repositório de pasta.
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
        // Arquivos .cmd do Windows precisam do shell. Python e outros
        // executáveis continuam sendo chamados diretamente.
        shell: options.shell ?? false,
        ...options,
    });

    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error(`Comando terminou com código ${result.status}: ${command}`);
    }

    return result;
}

function runNpm(args) {
    // Usar npm.cmd no Windows evita o EINVAL causado por spawnSync quando
    // um .cmd é executado sem shell. No Unix, npm é um executável normal.
    const command = isWin ? 'npm.cmd' : 'npm';
    return run(command, args, { shell: isWin });
}

function findCommand(candidates, args = ['--version']) {
    for (const candidate of candidates) {
        const result = spawnSync(candidate, args, {
            cwd: rootDir,
            stdio: 'ignore',
            shell: isWin && candidate.endsWith('.cmd'),
        });
        if (!result.error && result.status === 0) return candidate;
    }
    return null;
}

function getSystemPython() {
    // py -3 é preferível no Windows porque respeita o Python Launcher e não
    // depende de um python.exe antigo que tenha ficado no PATH.
    if (isWin) {
        const launcher = findCommand(['py']);
        if (launcher) return { command: launcher, prefix: ['-3'] };
    }

    const python = findCommand(isWin ? ['python'] : ['python3', 'python']);
    if (!python) {
        fail('Python 3 não encontrado. Instale Python 3 e execute o setup novamente.');
    }
    return { command: python, prefix: [] };
}

function getVenvPython() {
    return isWin
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');
}

function isVenvHealthy(venvPython) {
    if (!fs.existsSync(venvPython)) return false;

    const result = spawnSync(venvPython, ['-c', 'import sys; print(sys.executable)'], {
        cwd: rootDir,
        stdio: 'ignore',
        shell: false,
    });

    return !result.error && result.status === 0;
}

function ensureNode() {
    if (!findCommand(['node'])) {
        fail('Node.js não encontrado. Instale Node.js 18+ e execute o setup novamente.');
    }
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

function ensureVenv(python) {
    const venvDir = path.join(rootDir, '.venv');
    const venvPython = getVenvPython();

    // Um virtualenv contém caminhos internos para o Python usado na criação.
    // Se o projeto foi movido (por exemplo, C:\www -> H:\app), o executável
    // pode existir mas continuar apontando para o Python antigo. Nesse caso,
    // recriamos somente o .venv e preservamos todo o código do projeto.
    if (fs.existsSync(venvDir) && !isVenvHealthy(venvPython)) {
        log('[WARN] .venv existente está inválido ou aponta para outro caminho. Recriando...');
        fs.rmSync(venvDir, { recursive: true, force: true });
    }

    if (!fs.existsSync(venvPython)) {
        log('[INFO] Criando ambiente virtual Python local...');
        run(python.command, [...python.prefix, '-m', 'venv', '.venv']);
    }

    if (!isVenvHealthy(venvPython)) {
        fail(`O ambiente virtual não pôde ser inicializado corretamente: ${venvPython}`);
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

    // npm ci é determinístico quando o lockfile está presente. Em um clone
    // sem lockfile, npm install cria o lockfile e permite instalações futuras
    // com npm ci.
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
    ensureEnvFile();

    const systemPython = getSystemPython();
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
