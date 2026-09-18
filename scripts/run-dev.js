const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const rootDir = path.resolve(__dirname, '..');
const isWin = process.platform === 'win32';

function getVenvPython(){return isWin?path.join(rootDir,'.venv','Scripts','python.exe'):path.join(rootDir,'.venv','bin','python')}
function ensureEnvFile(){const p=path.join(rootDir,'.env'),e=path.join(rootDir,'.env.example');if(!fs.existsSync(p)&&fs.existsSync(e)){fs.copyFileSync(e,p);console.log('[OK] .env criado a partir do .env.example.')}}
function isPythonHealthy(python){if(!fs.existsSync(python))return false;const r=spawnSync(python,['-c','import sys; print(sys.executable)'],{cwd:rootDir,stdio:'ignore',shell:false});return !r.error&&r.status===0}
function hasFrontendDependencies(){const f=path.join(rootDir,'frontend','react','node_modules');return fs.existsSync(path.join(f,'.bin',isWin?'vite.cmd':'vite'))&&fs.existsSync(path.join(f,'.bin',isWin?'tsc.cmd':'tsc'))}
function runSetup(){const r=isWin?spawnSync(process.env.ComSpec||'cmd.exe',['/d','/s','/c','npm run setup'],{cwd:rootDir,stdio:'inherit',shell:false,env:process.env}):spawnSync('npm',['run','setup'],{cwd:rootDir,stdio:'inherit',shell:false,env:process.env});if(r.error)throw r.error;if(r.status!==0)throw new Error(`Setup terminou com código ${r.status}.`)}
function ensureSetup(){const p=getVenvPython(),d=path.join(rootDir,'frontend','react','dist','index.html');if(!isPythonHealthy(p)||!fs.existsSync(d)||!hasFrontendDependencies()){console.log('[INFO] Ambiente incompleto ou dependências do frontend ausentes. Executando npm run setup...');runSetup()}if(!isPythonHealthy(p))throw new Error(`Python virtualenv inválido: ${p}`);if(!hasFrontendDependencies())throw new Error('Dependências React ausentes. Execute `npm run setup`.');if(!fs.existsSync(d))throw new Error('Build React ausente: frontend/react/dist/index.html.')}
function spawnProcess(command,args,extraEnv={}){return spawn(command,args,{cwd:rootDir,stdio:'inherit',shell:false,env:{...process.env,...extraEnv}})}

// Filtra somente os access logs repetitivos do Flask/Werkzeug.
// Tracebacks e mensagens reais de erro continuam visíveis no terminal.
function isHttpAccessLog(line){return /^\s*\d{1,3}(?:\.\d{1,3}){3}.*\s-\s-\s\[.*\]\s".*"\s\d{3}\s/.test(line)}
function pipePythonStream(stream,writer,isError=false){const rl=readline.createInterface({input:stream});rl.on('line',line=>{if(!isHttpAccessLog(line))writer(line)})}
function spawnQuietPython(command,args,extraEnv={}){
 const child=spawn(command,args,{cwd:rootDir,stdio:['inherit','pipe','pipe'],shell:false,env:{...process.env,...extraEnv}});
 pipePythonStream(child.stdout,line=>console.log(line));
 pipePythonStream(child.stderr,line=>console.error(line),true);
 return child
}
function spawnNpm(args){if(!isWin)return spawnProcess('npm',args);return spawnProcess(process.env.ComSpec||'cmd.exe',['/d','/s','/c',['npm',...args.map(arg=>quoteCmdArg(String(arg)))].join(' ')])}
function quoteCmdArg(value){if(/^[A-Za-z0-9_./:=@%+,-]+$/.test(value))return value;return `"${value.replace(/"/g,'\\"')}"`}
function main(){ensureEnvFile();ensureSetup();startServers()}
function startServers(){console.log('[INFO] Iniciando backend, servidor público e frontend...');const python=getVenvPython();const backend=spawnQuietPython(python,['-m','src.app']);const publicServer=spawnQuietPython(python,['-m','src.public_server'],{PUBLIC_ONLY:'1'});const frontend=spawnNpm(['--prefix','frontend/react','run','dev','--','--host','0.0.0.0','--port','5173']);let stopping=false;const stop=(signal='SIGTERM')=>{if(stopping)return;stopping=true;for(const child of [backend,publicServer,frontend])if(!child.killed)child.kill(signal)};process.on('SIGINT',()=>{stop();process.exit(0)});process.on('SIGTERM',()=>{stop();process.exit(0)});const failIfUnexpectedExit=(name,code)=>{if(stopping)return;console.error(`[ERRO] ${name} encerrou inesperadamente (código ${code??0}).`);stop();process.exit(code||1)};for(const [child,name] of [[backend,'Backend'],[publicServer,'Servidor público'],[frontend,'Frontend']]){child.on('error',error=>{console.error(`[ERRO] Falha ao iniciar ${name}: ${error.message}`);stop();process.exit(1)});child.on('exit',code=>failIfUnexpectedExit(name,code))}}
try{main()}catch(error){console.error(`[ERRO] ${error.message}`);process.exit(1)}
