import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import serveStatic from 'serve-static'

const __dirname = dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        interactive: resolve(__dirname, 'interactive.html'),
      },
    },
  },
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
    // Serve data for D3 interactive viewer from public/data only (self-contained)
    // Run export_d3_data.py and export_d3_stops.py to populate public/data/
    {
      name: 'serve-data',
      configureServer(server) {
        server.middlewares.use(
          '/data',
          serveStatic(resolve(__dirname, 'public/data'))
        )
      },
    },
  ],
  server: {
    fs: { allow: ['..'] },
  },
})
