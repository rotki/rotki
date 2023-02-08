#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { ArgumentParser } = require('argparse');
const { build } = require('vite');
const { sharedConfig } = require('./setup');
const OUTPUT_DIR = 'dist';

const parser = new ArgumentParser({
  description: 'Rotki frontend build'
});
parser.add_argument('--mode', { help: 'mode docker', default: 'production' });
const { mode } = parser.parse_args();

const injectEnv = (envName = '.env') => {
  const envPath = path.resolve(__dirname, `../${envName}`);
  const envExists = fs.existsSync(envPath);
  if (envExists) {
    require('dotenv').config({ path: envPath, override: true });
  }
};

/**
 * @param {{name: string; configFile: string }} param0
 */
const getBuilder = ({ name, configFile }) => {
  return build({
    ...sharedConfig,
    mode,
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

    injectEnv('.env');
    if (mode === 'docker') {
      injectEnv('.env.docker');
    } else {
      await setupPreloadBuilder();
      await setupMainBuilder();
    }

    await setupRendererBuilder();
    console.log('Build is done!');
    process.exit(0);
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
})();
