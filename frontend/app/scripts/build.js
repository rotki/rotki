#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { ArgumentParser } from 'argparse';
import { build } from 'vite';
import { config } from 'dotenv';
import { sharedConfig } from './setup.js';

const OUTPUT_DIR = 'dist';
const __dirname = import.meta.dirname;

const parser = new ArgumentParser({
  description: 'Rotki frontend build',
});
parser.add_argument('--mode', { help: 'mode docker', default: 'production' });
const { mode } = parser.parse_args();

function injectEnv(envName = '.env') {
  const envPath = path.resolve(__dirname, `../${envName}`);
  const envExists = fs.existsSync(envPath);
  if (envExists)
    config({ path: envPath, override: true });
}

/**
 * @param {{name: string; configFile: string }} param0
 */
function getBuilder({ name, configFile }) {
  return build({
    ...sharedConfig,
    mode,
    configFile,
    plugins: [{ name }],
  });
}

function setupMainBuilder() {
  return getBuilder({
    name: 'build-main',
    configFile: 'vite.config.main.ts',
  });
}

function setupPreloadBuilder() {
  return getBuilder({
    name: 'build-preload',
    configFile: 'vite.config.preload.ts',
  });
}

function setupRendererBuilder() {
  return getBuilder({
    name: 'build-renderer',
    configFile: 'vite.config.ts',
  });
}

async function setup() {
  try {
    if (fs.existsSync(OUTPUT_DIR))
      fs.rmSync(OUTPUT_DIR, { recursive: true });

    injectEnv('.env');
    if (mode === 'docker') {
      injectEnv('.env.docker');
    }
    else {
      if (mode && mode !== 'production')
        injectEnv(`.env.${mode}`);

      await setupPreloadBuilder();
      await setupMainBuilder();
    }

    await setupRendererBuilder();
    console.log('Build is done!');
    process.exit(0);
  }
  catch (error) {
    console.error(error);
    process.exit(1);
  }
}

// re-evaluate after moving to mjs or ts
// eslint-disable-next-line unicorn/prefer-top-level-await
setup();
