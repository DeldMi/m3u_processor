const { exec } = require('child_process');
const os = require('os');

const url = 'http://127.0.0.1:5000';

const command = os.platform() === 'win32'
    ? `start "" "${url}"`
    : `xdg-open "${url}"`;

exec(command, (error) => {
    if (error) {
        console.warn(`[WARN] Nao foi possivel abrir o navegador automaticamente: ${error.message}`);
    }
});
