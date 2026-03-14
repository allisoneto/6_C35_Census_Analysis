import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import serveStatic from 'serve-static'

const __dirname = dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    svelte(),
    // Serve ../output at /output for visualization images
    {
      name: 'serve-output',
      configureServer(server) {
        server.middlewares.use(
          '/output',
          serveStatic(resolve(__dirname, '../output'))
        )
      },
    },
  ],
  server: {
    fs: { allow: ['..'] },
  },
})
