const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';
const dryRun = process.argv.includes('--dry-run');

function getNpmCommand() {
    const execPath = process.env.npm_execpath;
    if (execPath) {
        return {
            command: process.execPath,
            args: [execPath],
        };
    }

    return {
        command: isWin ? 'npm.cmd' : 'npm',
        args: [],
    };
}

function log(message) {
    console.log(message);
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

    if (result.error) {
        throw result.error;
    }

    if (result.status !== 0) {
        process.exit(result.status || 1);
    }

    return result;
}

function runNpm(args, options = {}) {
    const npmConfig = getNpmCommand();
    return run(npmConfig.command, [...npmConfig.args, ...args], options);
}

function getPythonCommand() {
    const candidates = [
        isWin ? 'py' : 'python3',
        isWin ? 'python' : 'python',
    ];

    for (const cmd of candidates) {
        const result = spawnSync(cmd, ['--version'], { stdio: 'ignore' });
        if (result.status === 0) {
            return cmd;
        }
    }

    throw new Error('Python 3 nao encontrado. Instale o Python 3.11+ antes de continuar.');
}

function getVenvPython() {
    return isWin
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');
}

function ensureEnvFile() {
    const envPath = path.join(rootDir, '.env');
    const examplePath = path.join(rootDir, '.env.example');
    if (fs.existsSync(envPath)) return;
    if (fs.existsSync(examplePath)) {
        fs.copyFileSync(examplePath, envPath);
        log('[OK] Arquivo .env criado a partir do .env.example');
    }
}

function ensureVenv(pythonCmd) {
    const venvPython = getVenvPython();
    if (!fs.existsSync(venvPython)) {
        run(pythonCmd, ['-m', 'venv', '.venv']);
    }
}

function installPythonDeps(venvPython) {
    run(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip']);
    run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt']);
}

function installFrontendDeps() {
    const frontendDir = path.join(rootDir, 'frontend', 'react');
    const lockPath = path.join(frontendDir, 'package-lock.json');

    if (fs.existsSync(lockPath)) {
        runNpm(['--prefix', 'frontend/react', 'ci']);
    } else {
        runNpm(['--prefix', 'frontend/react', 'install']);
    }

    runNpm(['--prefix', 'frontend/react', 'run', 'build']);
    installFrontendDeps();
    log('\n[OK] Ambiente configurado com sucesso.');
    log('Use: npm run start');
}

try {
    main();
} catch (error) {
    console.error(`\n[ERRO] ${error.message}`);
    process.exit(1);
}
