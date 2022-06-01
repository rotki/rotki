/* eslint-disable @typescript-eslint/no-var-requires */
const child_process = require('child_process');
const path = require('path');
const dotenv = require('dotenv').config({ path: __dirname + '/.env' });
const { DefinePlugin } = require('webpack');
const nodeExternals = require('webpack-node-externals');

if (!process.env.NODE_ENV) {
  process.env.NODE_ENV = 'development';
}

const environment = {};
if (dotenv.parsed) {
  Object.keys(dotenv.parsed).forEach((key) => {
    environment[key] = dotenv.parsed[key];
  });
}

module.exports = {
  entry: './src/index',
  mode: 'development',
  externals: [nodeExternals()],
  target: 'node',
  devtool: 'eval',
  watch: process.env.NODE_ENV === 'development',
  output: {
    path: path.resolve(__dirname, 'build'),
    filename: 'dist.js',
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.json'],
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  module: {
    rules: [
      {
        // Include ts, tsx, js, and jsx files.
        test: /\.(ts|js)x?$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
      },
      {
        test: /\.js$/,
        use: ['source-map-loader'],
        enforce: 'pre',
      },
    ],
  },
  plugins: [
    new DefinePlugin(environment),
    {
      apply: (compiler) => {
        compiler.hooks.done.tap('DonePlugin', (_stats) => {
          console.log('Compile is done !');
          setTimeout(() => {
            console.log('running proxy server');
            let dev = child_process.exec('npm run dev');
            dev.stdout.on('data', (data) =>
              console.log(data.replace(/^\s+|\s+$/g, ''))
            );
            dev.stderr.on('data', (data) =>
              console.error(data.replace(/^\s+|\s+$/g, ''))
            );
          });
        });
      },
    },
  ],
};
