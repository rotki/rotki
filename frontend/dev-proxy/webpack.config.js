/* eslint-disable @typescript-eslint/no-var-requires */
const path = require('path');
const nodeExternals = require('webpack-node-externals');
const WebpackShellPlugin = require('webpack-shell-plugin');

module.exports = {
  entry: './src/index',
  mode: 'development',
  externals: [nodeExternals()],
  target: 'node',
  devtool: 'false',
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
    new WebpackShellPlugin({
      onBuildEnd: ['npm run dev'],
    }),
  ],
};
