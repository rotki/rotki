/// <reference types="vitest" />
import { builtinModules } from 'module';
import { join, resolve } from 'path';
import { VuetifyResolver } from 'unplugin-vue-components/resolvers';
import Components from 'unplugin-vue-components/vite';
import ScriptSetup from 'unplugin-vue2-script-setup/vite';
import { defineConfig } from 'vite';
import { createVuePlugin as vue } from 'vite-plugin-vue2';

const PACKAGE_ROOT = __dirname;
const envPath = process.env.VUE_APP_PUBLIC_PATH;
const publicPath = envPath ? envPath : '/';
const isDevelopment = process.env.NODE_ENV === 'development';

if (envPath) {
  console.log(`A custom publicPath has been specified, using ${envPath}`);
}

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(PACKAGE_ROOT, 'src'),
      '~@': resolve(PACKAGE_ROOT, 'src')
    }
  },
  // @ts-ignore
  test: {
    globals: true,
    environment: 'jsdom',
    deps: {
      inline: ['vuetify']
    }
  },
  base: publicPath,
  define: {
    'process.env': { ...process.env }
  },
  plugins: [
    vue(),
    ScriptSetup(),
    Components({
      dts: true,
      include: [/\.vue$/, /\.vue\?vue/],
      resolvers: [VuetifyResolver()]
    })
  ],
  server: {
    port: 8080
  },
  build: {
    sourcemap: isDevelopment,
    outDir: 'dist',
    assetsDir: '.',
    minify: true,
    rollupOptions: {
      external: [
        'electron',
        'electron-devtools-installer',
        ...builtinModules.flatMap(p => [p, `node:${p}`])
      ],
      output: {
        entryFileNames: '[name].js'
      },
      input: join(PACKAGE_ROOT, 'index.html')
    },
    emptyOutDir: false
  }
});
