import * as fs from 'fs';
import { builtinModules } from 'module';
import { platform } from 'os';
import { join, parse } from 'path';
import { defineConfig, Plugin } from 'vite';

const PACKAGE_ROOT = __dirname;
const isDevelopment = process.env.NODE_ENV === 'development';

const binaryDependencyPlugin = (): Plugin => {
  let outDir = '';
  let rootDir = '';
  return {
    name: 'vite-plugin-binary-dependency',
    configResolved(config) {
      outDir = config.build.outDir;
      rootDir = config.root;
    },
    async writeBundle() {
      if (platform() !== 'win32') {
        console.log('ps-list vendor skipped');
        return;
      }
      const parsedPath = parse(rootDir);
      const psList = join(parsedPath.dir, 'node_modules', 'ps-list', 'vendor');
      const files = fs.readdirSync(psList);
      const output = join(rootDir, outDir, 'vendor');
      if (!fs.existsSync(output)) {
        fs.mkdirSync(output);
      }

      for (const file of files) {
        const src = join(psList, file);
        const dest = join(output, file);
        console.log(`${file} -> ${dest}`);
        fs.copyFileSync(src, dest);
      }
    }
  };
};

export default defineConfig({
  root: PACKAGE_ROOT,
  envDir: process.cwd(),
  resolve: {
    alias: {
      '@': join(PACKAGE_ROOT, 'src') + '/'
    }
  },
  plugins: [binaryDependencyPlugin()],
  build: {
    sourcemap: isDevelopment ? 'inline' : false,
    outDir: 'dist',
    assetsDir: '.',
    minify: !isDevelopment,
    lib: {
      entry: 'src/background.ts',
      formats: ['cjs']
    },
    rollupOptions: {
      external: [
        'csv',
        'electron',
        'electron-devtools-installer',
        ...builtinModules.flatMap(p => [p, `node:${p}`])
      ],
      output: {
        entryFileNames: '[name].js'
      }
    },
    emptyOutDir: false
  }
});
