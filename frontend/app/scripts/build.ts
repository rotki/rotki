#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';
import { config } from 'dotenv';
import { isEmpty } from 'es-toolkit/compat';
import { build } from 'vite';
import { type BuildOutput, sharedConfig } from './setup';

process.env.NODE_ENV = 'production';

const OUTPUT_DIR = 'dist';
const currentDirectory = import.meta.dirname;

function injectEnv(envName = '.env'): void {
  const envPath = path.resolve(currentDirectory, `../${envName}`);
  const envExists = fs.existsSync(envPath);
  if (envExists)
    config({ path: envPath, override: true });
}

async function getBuilder({ name, configFile, mode }: { name: string; configFile: string; mode: string }): Promise<BuildOutput> {
  return build({
    ...sharedConfig,
    mode,
    configFile,
    plugins: [{ name }],
  });
}

async function setupMainBuilder(mode: string): Promise<BuildOutput> {
  consola.box('Building main process');
  return getBuilder({
    name: 'build-main',
    configFile: 'vite.config.main.ts',
    mode,
  });
}

async function setupPreloadBuilder(mode: string): Promise<BuildOutput> {
  consola.box('Building preload process');
  return getBuilder({
    name: 'build-preload',
    configFile: 'vite.config.preload.ts',
    mode,
  });
}

async function setupRendererBuilder(mode: string): Promise<BuildOutput> {
  consola.box('Building renderer process');
  return getBuilder({
    name: 'build-renderer',
    configFile: 'vite.config.ts',
    mode,
  });
}

function cleanupDist(): void {
  if (fs.existsSync(OUTPUT_DIR))
    fs.rmSync(OUTPUT_DIR, { recursive: true });
}

/**
 * If the env already contains env variables about the backend urls,
 * e.g., from the e2e script, then we want to keep these settings.
 */
function loadUrlConfig(mode: string): Record<string, string> {
  const urlsVars: Record<string, string> = {};
  if (mode !== 'e2e') {
    return urlsVars;
  }
  const backendUrl = process.env.VITE_BACKEND_URL;
  const colibriUrl = process.env.VITE_COLIBRI_URL;
  if (backendUrl)
    urlsVars.VITE_BACKEND_URL = backendUrl;
  if (colibriUrl)
    urlsVars.VITE_COLIBRI_URL = colibriUrl;
  return urlsVars;
}

function updateEnvVars(vars: Record<string, string>): void {
  if (isEmpty(vars)) {
    return;
  }
  for (const [key, value] of Object.entries(vars)) {
    process.env[key] = value;
  }
}

async function setup(mode: string): Promise<void> {
  consola.info(`Building for ${mode}...`);
  const urlsVars: Record<string, string> = loadUrlConfig(mode);

  try {
    cleanupDist();

    injectEnv('.env');
    if (mode === 'docker') {
      injectEnv('.env.docker');
    }
    else {
      if (mode && mode !== 'production')
        injectEnv(`.env.${mode}`);
      updateEnvVars(urlsVars);

      await setupPreloadBuilder(mode);
      await setupMainBuilder(mode);
    }

    await setupRendererBuilder(mode);

    consola.info('Build is complete!');
    process.exit(0);
  }
  catch (error) {
    consola.error(error);
    process.exit(1);
  }
}

const cli = cac();

cli.command('', 'Rotki frontend build')
  .option('--mode <mode>', 'Build mode (production, docker, e2e)', { default: 'production' })
  .action(async (options) => {
    await setup(options.mode);
  });

cli.help();
cli.parse();
