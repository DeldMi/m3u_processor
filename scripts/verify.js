/**
 * Verificador oficial do projeto.
 * Sempre usa o Python do .venv quando ele existe e falha de forma explícita
 * quando o ambiente local está incompleto.
 */
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..');
const isWindows = process.platform === 'win32';
const venvPython = isWindows ? path.join(ROOT,'.venv','Scripts','python.exe') : path.join(ROOT,'.venv','bin','python');

function run(command,args,label){
    console.log(`\n==> ${label}`);
    const result=spawnSync(command,args,{cwd:ROOT,stdio:'inherit',shell:false,env:{...process.env}});
    if(result.error){console.error(`Falha ao executar ${label}: ${result.error.message}`);return false;}
    if(result.status!==0){console.error(`${label} terminou com código ${result.status}.`);return false;}
    return true;
}

function runNpm(args,label){
    if(!isWindows)return run('npm',args,label);
    return run(process.env.ComSpec||'cmd.exe',['/d','/s','/c',`npm.cmd ${args.join(' ')}`],label);
}

function findPython(){
    const candidates=fs.existsSync(venvPython)?[venvPython]:(isWindows?['py','python']:['python3','python']);
    for(const candidate of candidates){const result=spawnSync(candidate,['--version'],{cwd:ROOT,stdio:'ignore',shell:false});if(!result.error&&result.status===0)return candidate;}
    return null;
}

let ok=true;
const python=findPython();
if(!python){console.error('Python não encontrado. Execute `npm run setup`.');ok=false;}
else{
    ok=run(python,['-m','compileall','-q','src'],'Sintaxe Python')&&ok;
    ok=run(python,['-m','unittest','discover','-s','tests','-v'],'Testes Python')&&ok;
}
const frontend=path.join(ROOT,'frontend','react');
if(!fs.existsSync(path.join(frontend,'node_modules'))){console.error('Dependências React ausentes. Execute `npm run setup`.');ok=false;}
else ok=runNpm(['--prefix','frontend/react','run','build'],'Build React/TypeScript')&&ok;
for(const required of ['AGENTS.md','LICENSE','NOTICE','package.json','frontend/react/src/main.tsx'])if(!fs.existsSync(path.join(ROOT,required))){console.error(`Arquivo obrigatório ausente: ${required}`);ok=false;}
console.log(`\n${ok?'VERIFICAÇÃO CONCLUÍDA COM SUCESSO.':'VERIFICAÇÃO ENCONTROU FALHAS.'}`);
process.exitCode=ok?0:1;
