import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
    // `loadEnv` aceita um diretório explícito; assim a configuração não depende
    // de `process` nem exige @types/node durante o typecheck do frontend.
    const env = loadEnv(mode, '.', '')
    const cloudflare = env.CF_PAGES === '1' || env.CLOUDFLARE_PAGES === '1'

    return {
        plugins: [react()],
        // Flask serve a SPA localmente em /app-assets/. No Cloudflare Pages,
        // a aplicação é publicada na raiz do domínio.
        base: cloudflare ? '/' : '/app-assets/',
        css: {
            preprocessorOptions: {
                scss: {
                    additionalData: '$text: #f4f7f8;'
                }
            }
        },
        server: {
            port: 5173,
            proxy: {
                '/api': 'http://127.0.0.1:5000',
                '/login': 'http://127.0.0.1:5000',
                '/logout': 'http://127.0.0.1:5000',
                '/playlist': 'http://127.0.0.1:5000',
                '/epg': 'http://127.0.0.1:5000'
            }
        },
    }
})
