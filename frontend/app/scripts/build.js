#!/usr/bin/env node

const fs = require('fs');
const { build } = require('vite');
require('dotenv').config();

const { sharedConfig } = require('./setup');
const OUTPUT_DIR = 'dist';

/**
 * @param {{name: string; configFile: string }} param0
 */
const getBuilder = ({ name, configFile }) => {
  return build({
    ...sharedConfig,
    configFile,
    plugins: [{ name }]
  });
};

const setupMainBuilder = () => {
  return getBuilder({
    name: 'build-main',
    configFile: 'vite.config.main.ts'
  });
};

const setupPreloadBuilder = () => {
  return getBuilder({
    name: 'build-preload',
    configFile: 'vite.config.preload.ts'
  });
};

const setupRendererBuilder = () => {
  return getBuilder({
    name: 'build-renderer',
    configFile: 'vite.config.ts'
  });
};

(async () => {
  try {
    if (fs.existsSync(OUTPUT_DIR)) {
      fs.rmSync(OUTPUT_DIR, { recursive: true });
    }
    await setupPreloadBuilder();
    await setupMainBuilder();
    const watcher = await setupRendererBuilder();
    watcher.on('event', event => {
      if (event.code === 'END') {
        console.log('Build is done!');
        process.exit(0);
      }
    });
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
})();
