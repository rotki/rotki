import path from "path";
import alias from '@rollup/plugin-alias';
import typescript from 'rollup-plugin-typescript2'
import pkg from './package.json'

const projectRootDir = path.resolve(__dirname);

export default {
  input: 'src/index.ts',
  output: [
    {
      file: pkg.main,
      sourcemap: true,
      format: 'cjs',
    },
    {
      file: pkg.module,
      sourcemap: true,
      format: 'es',
    },
  ],
  external: [
    ...Object.keys(pkg.dependencies || {}),
    ...Object.keys(pkg.peerDependencies || {}),
  ],
  plugins: [
    typescript({
      typescript: require('typescript'),
    }),
    alias({
      entries: [
        { find: '@', replacement: path.resolve(projectRootDir, 'src')}
      ]
    })
  ],
}