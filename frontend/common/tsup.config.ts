import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  splitting: true,
  dts: true,
  minify: false,
  bundle: true,
  skipNodeModulesBundle: true,
  target: 'es2020',
  outDir: 'lib',
  format: ['esm'],
  sourcemap: true,
  clean: true,
  external: ['zod', 'vue', '@vueuse/core', 'bignumber.js'],
});
