import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    base: '/app-assets/',
    css: {
        preprocessorOptions: {
            scss: {
                // Legacy styles.scss references $text; keep the build deterministic
                // while the existing palette continues to use $ink internally.
                additionalData: '$text: #f4f7f8;'
            }
        }
    },
    server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:5000', '/login': 'http://127.0.0.1:5000', '/logout': 'http://127.0.0.1:5000', '/playlist': 'http://127.0.0.1:5000', '/epg': 'http://127.0.0.1:5000' } },
})