/**
 * Verificador oficial do projeto.
 *
 * A rotina é deliberadamente simples e cross-platform para funcionar em
 * Windows, Linux e macOS sem depender de ferramentas externas adicionais.
 */
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const isWindows = process.platform === "win32";
const npmCommand = isWindows ? "npm.cmd" : "npm";
const pythonCandidates = isWindows ? ["python", "py"] : ["python3", "python"];

function run(command, args, label, options = {}) {
    console.log(`\n==> ${label}`);
    const result = spawnSync(command, args, {
        cwd: ROOT,
        stdio: "inherit",
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
        const result = spawnSync(candidate, ["--version"], { cwd: ROOT, stdio: "ignore", shell: false });
        if (!result.error && result.status === 0) return candidate;
    }
    return null;
}

let ok = true;
const python = findPython();
if (!python) {
    console.error("Python não encontrado. Instale Python 3 antes de executar verify.");
    ok = false;
} else {
    ok = run(python, ["-m", "compileall", "-q", "src"], "Sintaxe Python") && ok;
    ok = run(python, ["-m", "unittest", "discover", "-s", "tests", "-v"], "Testes Python") && ok;
}

const frontendDir = path.join(ROOT, "frontend", "react");
const frontendModules = path.join(frontendDir, "node_modules");
if (!fs.existsSync(frontendModules)) {
    console.error("Dependências do frontend não encontradas. Execute `npm run setup` primeiro.");
    ok = false;
} else {
    ok = run(npmCommand, ["--prefix", "frontend/react", "run", "build"], "Build React/TypeScript") && ok;
}

for (const required of ["AGENTS.md", "LICENSE", "NOTICE", "package.json", "frontend/react/src/main.tsx"]) {
    if (!fs.existsSync(path.join(ROOT, required))) {
        console.error(`Arquivo obrigatório ausente: ${required}`);
        ok = false;
    }
}

console.log(`\n${ok ? "VERIFICAÇÃO CONCLUÍDA COM SUCESSO." : "VERIFICAÇÃO ENCONTROU FALHAS."}`);
process.exitCode = ok ? 0 : 1;
