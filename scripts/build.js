const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const BUILD_DIR = path.join(ROOT, 'build');
const PACKAGE_DIR = path.join(BUILD_DIR, 'm3u-processor');
const isWindows = process.platform === 'win32';
const pythonCandidates = isWindows
    ? [path.join(ROOT, '.venv', 'Scripts', 'python.exe'), 'py', 'python']
    : [path.join(ROOT, '.venv', 'bin', 'python'), 'python3', 'python'];

function run(command, args, label, options = {}) {
    console.log(`\n==> ${label}`);
    const result = spawnSync(command, args, {
        cwd: ROOT,
        stdio: 'inherit',
        shell: false,
        env: { ...process.env },
        ...options,
    });
    if (result.error) throw new Error(`${label}: ${result.error.message}`);
    if (result.status !== 0) throw new Error(`${label}: processo terminou com código ${result.status}`);
    return result;
}

function runNpm(args, label) {
    if (!isWindows) return run('npm', args, label);

    // No Windows, npm.cmd via spawnSync pode retornar EINVAL dependendo do
    // ambiente. cmd.exe é o mecanismo nativo para executar arquivos .cmd.
    const commandLine = ['npm', ...args.map((arg) => quoteCmdArg(String(arg)))].join(' ');
    return run(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', commandLine], label);
}

function quoteCmdArg(value) {
    if (/^[A-Za-z0-9_./:=@%+,-]+$/.test(value)) return value;
    return `"${value.replace(/"/g, '\\"')}"`;
}

function findPython() {
    for (const candidate of pythonCandidates) {
        if (path.isAbsolute(candidate) && !fs.existsSync(candidate)) continue;
        const result = spawnSync(candidate, ['--version'], { cwd: ROOT, stdio: 'ignore', shell: false });
        if (!result.error && result.status === 0) return candidate;
    }
    throw new Error('Python não encontrado. Execute `npm run setup` primeiro.');
}

function copyTree(source, destination, options = {}) {
    if (!fs.existsSync(source)) return;
    fs.cpSync(source, destination, {
        recursive: true,
        force: true,
        filter: options.filter,
    });
}

function copyFile(relativePath) {
    const source = path.join(ROOT, relativePath);
    if (!fs.existsSync(source)) return;
    const destination = path.join(PACKAGE_DIR, relativePath);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
}

function frontendSourceFilter(source) {
    const relative = path.relative(path.join(ROOT, 'frontend', 'react'), source).replaceAll('\\', '/');
    if (!relative) return true;
    return !/(^|\/)(node_modules|dist|\.vite|coverage|\.cache)(\/|$)/.test(relative);
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

    for (const directory of ['src', 'scripts', 'tests', 'functions', 'cloudflare']) {
        copyTree(path.join(ROOT, directory), path.join(PACKAGE_DIR, directory));
    }

    // O ZIP representa o projeto inteiro: código-fonte do frontend + artefato
    // compilado, sem node_modules, caches ou o dist duplicado na cópia-fonte.
    copyTree(
        path.join(ROOT, 'frontend', 'react'),
        path.join(PACKAGE_DIR, 'frontend', 'react'),
        { filter: frontendSourceFilter },
    );
    copyTree(
        path.join(ROOT, 'frontend', 'react', 'dist'),
        path.join(PACKAGE_DIR, 'frontend', 'react', 'dist'),
    );

    fs.writeFileSync(
        path.join(PACKAGE_DIR, 'BUILD_INFO.txt'),
        [
            'M3U Processor / M3U Architect',
            `Build UTC: ${new Date().toISOString()}`,
            'Conteúdo: projeto completo, backend Python, frontend-fonte, frontend compilado, scripts, testes e configuração de deploy.',
            'Não inclui: .env, banco de dados, logs, output/input, node_modules, .venv e caches.',
        ].join('\n') + '\n',
        'utf8',
    );
}

function removePythonCaches() {
    const roots = [path.join(ROOT, 'src'), path.join(ROOT, 'tests')];
    for (const root of roots) {
        if (!fs.existsSync(root)) continue;
        const entries = fs.readdirSync(root, { withFileTypes: true });
        for (const entry of entries) {
            if (!entry.isDirectory() || entry.name !== '__pycache__') continue;
            fs.rmSync(path.join(root, entry.name), { recursive: true, force: true });
        }
    }
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
    ].join('\n');
    run(python, ['-c', script, PACKAGE_DIR, zipPath], 'Empacotamento ZIP');
    return zipPath;
}

function main() {
    const python = findPython();
    const frontendNodeModules = path.join(ROOT, 'frontend', 'react', 'node_modules');
    const tsc = path.join(frontendNodeModules, '.bin', isWindows ? 'tsc.cmd' : 'tsc');

    if (!fs.existsSync(tsc)) {
        throw new Error(
            'Dependências do frontend incompletas: TypeScript não encontrado em frontend/react/node_modules/.bin. ' +
            'Execute `npm run setup` e tente novamente.'
        );
    }

    runNpm(['--prefix', 'frontend/react', 'run', 'build'], 'Build do frontend React/TypeScript');
    run(python, ['-m', 'compileall', '-q', 'src', 'tests'], 'Validação/compilação Python');
    removePythonCaches();
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
