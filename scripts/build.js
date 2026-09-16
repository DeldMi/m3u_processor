const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const BUILD_DIR = path.join(ROOT, 'build');
const PACKAGE_DIR = path.join(BUILD_DIR, 'm3u-processor');
const isWindows = process.platform === 'win32';
const npmCommand = isWindows ? 'npm.cmd' : 'npm';
const pythonCandidates = isWindows
    ? [path.join(ROOT, '.venv', 'Scripts', 'python.exe'), 'py', 'python']
    : [path.join(ROOT, '.venv', 'bin', 'python'), 'python3', 'python'];

function run(command, args, label, options = {}) {
    console.log(`\n==> ${label}`);
    const result = spawnSync(command, args, {
        cwd: ROOT,
        stdio: 'inherit',
        shell: options.shell ?? (isWindows && command === npmCommand),
        env: { ...process.env, ...(options.env || {}) },
    });
    if (result.error) throw new Error(`${label}: ${result.error.message}`);
    if (result.status !== 0) throw new Error(`${label}: processo terminou com código ${result.status}`);
}

function findPython() {
    for (const candidate of pythonCandidates) {
        if (path.isAbsolute(candidate) && !fs.existsSync(candidate)) continue;
        const result = spawnSync(candidate, ['--version'], { cwd: ROOT, stdio: 'ignore', shell: false });
        if (!result.error && result.status === 0) return candidate;
    }
    throw new Error('Python não encontrado. Execute `npm run setup` primeiro.');
}

function copyTree(source, destination) {
    if (!fs.existsSync(source)) return;
    fs.cpSync(source, destination, { recursive: true, force: true });
}

function copyFile(relativePath) {
    const source = path.join(ROOT, relativePath);
    if (!fs.existsSync(source)) return;
    const destination = path.join(PACKAGE_DIR, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
}

function collectProject() {
    fs.rmSync(BUILD_DIR, { recursive: true, force: true });
    fs.mkdirSync(PACKAGE_DIR, { recursive: true });

    const files = [
        'AGENTS.md', 'LICENSE', 'NOTICE', 'README.md',
        'package.json', 'package-lock.json', '.env.example',
        'requirements.txt', 'Dockerfile', 'docker-compose.yml',
        'wrangler.toml',
    ];
    files.forEach(copyFile);

    for (const directory of ['src', 'scripts', 'tests', 'frontend/react/dist', 'functions', 'cloudflare']) {
        copyTree(path.join(ROOT, directory), path.join(PACKAGE_DIR, directory));
    }

    fs.writeFileSync(
        path.join(PACKAGE_DIR, 'BUILD_INFO.txt'),
        [
            'M3U Processor / M3U Architect',
            `Build UTC: ${new Date().toISOString()}`,
            'Conteúdo: backend Python, frontend compilado, scripts, testes e configuração de deploy.',
            'Não inclui: .env, banco de dados, logs, output/input, node_modules, .venv e caches.',
        ].join('\n') + '\n',
        'utf8',
    );
}

function createZip(python) {
    const zipPath = path.join(BUILD_DIR, 'm3u-processor-build.zip');
    const script = [
        'import os, zipfile, sys',
        'src, dst = sys.argv[1], sys.argv[2]',
        'with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:',
        '    for root, dirs, files in os.walk(src):',
        '        for name in files:',
        '            path = os.path.join(root, name)',
        '            z.write(path, os.path.relpath(path, os.path.dirname(src)))',
    ].join(';');
    run(python, ['-c', script, PACKAGE_DIR, zipPath], 'Empacotamento ZIP');
    return zipPath;
}

function main() {
    const python = findPython();

    // O build raiz é deliberadamente diferente do build do frontend: ele
    // primeiro compila o React e depois monta um pacote executável do projeto.
    run(npmCommand, ['--prefix', 'frontend/react', 'run', 'build'], 'Build do frontend React/TypeScript', { shell: isWindows });
    run(python, ['-m', 'compileall', '-q', 'src', 'tests'], 'Validação/compilação Python');
    collectProject();
    const zipPath = createZip(python);

    console.log('\nBUILD COMPLETO CONCLUÍDO.');
    console.log(`Diretório: ${BUILD_DIR}`);
    console.log(`ZIP: ${zipPath}`);
}

try {
    main();
} catch (error) {
    console.error(`\n[ERRO] ${error.message}`);
    process.exit(1);
}
