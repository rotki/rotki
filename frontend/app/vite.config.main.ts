import * as fs from 'node:fs';
import { builtinModules } from 'node:module';
import { platform } from 'node:os';
import { join, parse } from 'node:path';
import process from 'node:process';
import { defineConfig, type Plugin } from 'vite';

const PACKAGE_ROOT = __dirname;
const isDevelopment = process.env.NODE_ENV === 'development';

function binaryDependencyPlugin(): Plugin {
  let outDir = '';
  let rootDir = '';
  return {
    name: 'vite-plugin-binary-dependency',
    configResolved(config) {
      outDir = config.build.outDir;
      rootDir = config.root;
    },
    writeBundle() {
      if (platform() !== 'win32') {
        console.log('ps-list vendor skipped');
        return;
      }
      const parsedPath = parse(rootDir);
      const psList = join(parsedPath.dir, 'app', 'node_modules', 'ps-list', 'vendor');
      const files = fs.readdirSync(psList);
      const output = join(rootDir, outDir, 'vendor');
      if (!fs.existsSync(output))
        fs.mkdirSync(output);

      for (const file of files) {
        const src = join(psList, file);
        const dest = join(output, file);
        console.log(`${file} -> ${dest}`);
        fs.copyFileSync(src, dest);
      }
    },
  };
}

export default defineConfig({
  root: PACKAGE_ROOT,
  envDir: process.cwd(),
  resolve: {
    alias: {
      '@electron': `${join(PACKAGE_ROOT, 'electron')}/`,
      '@shared': `${join(PACKAGE_ROOT, 'shared')}/`,
    },
  },
  plugins: [binaryDependencyPlugin()],
  ssr: {
    noExternal: true,
  },
  build: {
    sourcemap: isDevelopment ? 'inline' : false,
    target: 'node22',
    outDir: 'dist',
    assetsDir: '.',
    ssr: true,
    minify: !isDevelopment,
    lib: {
      entry: 'electron/main/index.ts',
      formats: ['es'],
    },
    rollupOptions: {
      external: ['electron', ...builtinModules.flatMap(p => [p, `node:${p}`])],
      output: {
        entryFileNames: 'main.js',
        manualChunks(id) {
          if (id.includes('node_modules'))
            return 'background-vendor';
          if (id.includes('electron-updater'))
            return 'background-vendor-updater';
          if (id.includes('subprocess-handler'))
            return 'background-subprocess-handler';
          if (id.includes('http'))
            return 'background-http';
        },
      },
    },
    emptyOutDir: false,
  },
  esbuild: {
    target: 'node22',
  },
});
