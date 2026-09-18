const { spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const dryRun = process.argv.includes('--dry-run');

function log(message) { console.log(message); }
function fail(message) { throw new Error(message); }

function run(command, args, options = {}) {
    log(`> ${command} ${args.join(' ')}`);
    if (dryRun) return { status: 0 };
    const result = spawnSync(command, args, {
        cwd: rootDir,
        stdio: 'inherit',
        shell: options.shell ?? false,
        ...options,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`Comando terminou com código ${result.status}: ${command}`);
    return result;
}

function runNpm(args) {
    if (!isWin) return run('npm', args);
    // No Windows, executar npm.cmd diretamente com spawnSync pode produzir
    // EINVAL em algumas combinações de Node/Windows. cmd.exe é mais estável.
    const commandLine = ['npm', ...args.map((arg) => quoteCmdArg(String(arg)))].join(' ');
    return run(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', commandLine], { shell: false });
}

function quoteCmdArg(value) {
    if (/^[A-Za-z0-9_./:=@%+,-]+$/.test(value)) return value;
    return `"${value.replace(/"/g, '\\"')}"`;
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
    if (isWin) {
        const launcher = findCommand(['py'], ['-3', '--version']);
        if (launcher) return { command: launcher, prefix: ['-3'] };
    }
    const python = findCommand(isWin ? ['python'] : ['python3', 'python']);
    if (!python) fail('Python 3 não encontrado. Instale Python 3 e execute o setup novamente.');
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
        cwd: rootDir, stdio: 'ignore', shell: false,
    });
    return !result.error && result.status === 0;
}

function ensureNode() {
    if (!findCommand(['node'])) fail('Node.js não encontrado. Instale Node.js 18+ e execute o setup novamente.');
}

function ensureInitialAdminPassword() {
    const envPath = path.join(rootDir, '.env');
    if (!fs.existsSync(envPath)) return;
    const current = fs.readFileSync(envPath, 'utf8');
    if (/^ADMIN_INITIAL_PASSWORD\\s*=\\s*['"]?[^'"]+['"]?\\s*$/m.test(current)) return;
    const password = crypto.randomBytes(18).toString('base64url');
    fs.appendFileSync(envPath, `\\nADMIN_INITIAL_PASSWORD='${password}'\\n`, 'utf8');
    log('[OK] Senha inicial do administrador criada em .env.');
}
function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (fs.existsSync(envPath)) return;
    if (!fs.existsSync(examplePath)) fail('Arquivo .env.example não encontrado; não foi possível criar o .env.');
    fs.copyFileSync(examplePath, envPath);
    log('[OK] Arquivo .env criado a partir do .env.example.');
}

function ensureVenv(python) {
    const venvDir = path.join(rootDir, '.venv');
    const venvPython = getVenvPython();
    if (fs.existsSync(venvDir) && !isVenvHealthy(venvPython)) {
        log('[WARN] .venv existente está inválido ou aponta para outro caminho. Recriando...');
        fs.rmSync(venvDir, { recursive: true, force: true });
    }
    if (!fs.existsSync(venvPython)) {
        log('[INFO] Criando ambiente virtual Python local...');
        run(python.command, [...python.prefix, '-m', 'venv', '.venv']);
    }
    if (!isVenvHealthy(venvPython)) fail(`O ambiente virtual não pôde ser inicializado corretamente: ${venvPython}`);
    return venvPython;
}

function installPythonDeps(venvPython) {
    run(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip']);
    run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt']);
}

function frontendBin(name) {
    return path.join(rootDir, 'frontend', 'react', 'node_modules', '.bin', isWin ? `${name}.cmd` : name);
}

function frontendDepsHealthy() {
    return fs.existsSync(frontendBin('vite')) && fs.existsSync(frontendBin('tsc'));
}

function cleanFrontendNodeModules(nodeModules) {
    try {
        if (fs.existsSync(nodeModules)) {
            fs.rmSync(nodeModules, { recursive: true, force: true, maxRetries: 10, retryDelay: 500 });
        }
        return true;
    } catch (error) {
        log(`[ERRO] O Windows não conseguiu remover frontend/react/node_modules: ${error.message}`);
        log('[ERRO] Um processo está mantendo arquivos abertos, provavelmente esbuild.exe, vite ou Node.js.');
        return false;
    }
}

function installFrontendDeps() {
    const frontendDir = path.join(rootDir, 'frontend', 'react');
    const packageJson = path.join(frontendDir, 'package.json');
    const lockPath = path.join(frontendDir, 'package-lock.json');
    const nodeModules = path.join(frontendDir, 'node_modules');

    if (!fs.existsSync(packageJson)) fail('frontend/react/package.json não encontrado.');

    if (dryRun) {
        log('[DRY-RUN] Instalação das dependências do frontend ignorada.');
        return;
    }

    const installArgs = fs.existsSync(lockPath)
        ? ['--prefix', 'frontend/react', 'ci']
        : ['--prefix', 'frontend/react', 'install'];

    let firstError = null;
    try {
        runNpm(installArgs);
    } catch (error) {
        firstError = error;
    }

    if (firstError) {
        // npm ci pode falhar porque o Windows não consegue substituir um
        // binário nativo (especialmente esbuild.exe). Não presumimos a causa;
        // verificamos se o conjunto de ferramentas realmente ficou utilizável.
        if (!isWin || frontendDepsHealthy()) throw firstError;

        log('[WARN] A instalação npm não terminou corretamente e o frontend ainda está incompleto.');
        log('[INFO] Tentando uma recuperação limpa de frontend/react/node_modules...');

        if (!cleanFrontendNodeModules(nodeModules)) {
            fail(
                'Não foi possível liberar frontend/react/node_modules. ' +
                'Feche todas as janelas do M3U Processor, Vite, Node.js, Cursor/VS Code e terminais que estejam usando o projeto. ' +
                'Depois execute `taskkill /F /IM node.exe /T` e rode `npm run setup` novamente.'
            );
        }

        runNpm(installArgs);
    }

    if (!frontendDepsHealthy()) {
        fail('As dependências do frontend foram instaladas, mas Vite/TypeScript não estão disponíveis em frontend/react/node_modules/.bin.');
    }

    runNpm(['--prefix', 'frontend/react', 'run', 'build']);

    const distIndex = path.join(frontendDir, 'dist', 'index.html');
    if (!fs.existsSync(distIndex)) fail('Build React terminou sem gerar frontend/react/dist/index.html.');
}

function main() {
    log('=== M3U Processor - Setup ===');
    ensureNode();
    ensureEnvFile();
    ensureInitialAdminPassword();
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

try { main(); } catch (error) {
    console.error(`\n[ERRO] ${error.message}`);
    process.exit(1);
}
