#!/usr/bin/env node

import { execSync } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import process from 'node:process';
import { ArgumentParser } from 'argparse';
import consola from 'consola';
import { config } from 'dotenv';
import { startAndTest } from 'start-server-and-test';

const parser = new ArgumentParser({
  description: 'e2e tests',
});

parser.add_argument('--ci', {
  help: 'will run e2e tests in headless mode',
  action: 'store_true',
});
parser.add_argument('--spec', { help: 'specific spec to run ' });
parser.add_argument('--browser', {
  help: 'specify browser to use when running ',
});
const { ci, spec, browser } = parser.parse_args();

config({
  path: path.join(process.cwd(), '.env.e2e'),
});

const BASE_PORT = 30301;

async function isPortAvailable(port: number): Promise<boolean> {
  return new Promise<boolean>((resolve, reject) => {
    const server = net.createServer();

    server.unref();

    server.once('error', (err: any) => {
      if (err.code === 'EADDRINUSE' || err.code === 'EACCES')
        resolve(false);
      else
        reject(err instanceof Error ? err : new Error(err));
    });

    server.once('listening', () => {
      server.close(() => resolve(true));
    });

    server.listen(port, '127.0.0.1');
  });
}

async function selectPort(startPort: number): Promise<number> {
  for (let portNumber = startPort; portNumber <= 65535; portNumber++) {
    if (await isPortAvailable(portNumber))
      return portNumber;
  }
  throw new Error('no free ports found');
}

const testDir = path.join(process.cwd(), '.e2e');
const dataDir = path.join(testDir, 'data');
const logDir = path.join(testDir, 'logs');

function cleanupData(): void {
  consola.info(`Cleaning up ${dataDir}`);
  const contents = fs.readdirSync(dataDir);
  for (const name of contents) {
    if (['images', 'global'].includes(name))
      continue;

    const currentPath = path.join(dataDir, name);
    if (fs.statSync(currentPath).isDirectory())
      fs.rmSync(currentPath, { recursive: true });
  }
}

if (!fs.existsSync(dataDir)) {
  consola.info(`Creating data directory: ${dataDir}`);
  fs.mkdirSync(dataDir, { recursive: true });
}

if (!fs.existsSync(logDir)) {
  consola.info(`Creating log directory: ${logDir}`);
  fs.mkdirSync(logDir, { recursive: true });
}

const frontendPort = await selectPort(BASE_PORT);
const backendPort = await selectPort(frontendPort + 1);
const colibriPort = await selectPort(backendPort + 1);

const colibriUrl = `http://127.0.0.1:${colibriPort}`;
const backendUrl = `http://127.0.0.1:${backendPort}`;
const frontendUrl = `http://localhost:${frontendPort}`;

process.env.CYPRESS_BACKEND_URL = backendUrl;
process.env.VITE_BACKEND_URL = backendUrl;
process.env.VITE_COLIBRI_URL = colibriUrl;

// Running the command with pnpm will cause the commands to exit with ELIFECYCLE Command failed.
// If we find away around this, we should change to pnpm.
const frontendCmd = ci ? 'vite preview' : 'tsx scripts/serve.ts --web';

const services = [
  {
    start: `tsx scripts/start-backend.ts --port ${backendPort} --data ${dataDir} --logs ${logDir}`,
    url: `${backendUrl}/api/1/ping`,
  },
  {
    start: `tsx scripts/start-colibri.ts --port ${colibriPort} --data ${dataDir} --logs ${logDir}`,
    url: `${colibriUrl}/health`,
  },
  {
    start: `${frontendCmd} --port ${frontendPort}`,
    url: frontendUrl,
  },
];

const testCmd = ci ? 'pnpm run cypress:run' : 'pnpm run cypress:open';

let test = testCmd;
if (spec)
  test += ` --spec **/${spec}`;

if (browser)
  test += ` --browser ${browser}`;

test += ` --config baseUrl=${frontendUrl}`;

if (ci && !process.env.SKIP_REBUILD) {
  consola.info('Building frontend');
  const start = Date.now();
  execSync('pnpm run build:app --mode e2e', { stdio: 'inherit' });
  consola.info(`Build complete (${Date.now() - start} ms)`);
}

async function run(): Promise<void> {
  try {
    await startAndTest({
      services,
      test,
      namedArguments: { expect: 200 },
    });
    consola.info('Execution completed successfully');
    cleanupData();
    process.exit(0);
  }
  catch (error) {
    consola.error('Command execution failed', error);
    cleanupData();
    process.exit(1);
  }
}

await run();
