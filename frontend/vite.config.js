import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 分包策略：将大型依赖拆分为独立 chunk，利用浏览器缓存
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, '/')
          if (normalizedId.includes('node_modules/vue/') || normalizedId.includes('node_modules/@vue/')) {
            return 'vendor-vue'
          }
          if (normalizedId.includes('node_modules/element-plus/')) {
            return 'vendor-element'
          }
          if (normalizedId.includes('node_modules/dayjs/')) {
            return 'vendor-dayjs'
          }
        },
      },
    },
    // CSS 代码分割
    cssCodeSplit: true,
    // 资源内联阈值 4KB
    assetsInlineLimit: 4096,
    // 启用 CSS 压缩
    cssMinify: true,
    // chunk 大小警告阈值
    chunkSizeWarningLimit: 500,
  },
})
