#!/usr/bin/env node

import { type ChildProcess, spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';
import { config } from 'dotenv';

config({
  path: path.join(process.cwd(), '.env.contract'),
});

const backendUrl = process.env.VITE_BACKEND_URL;

interface ContractOptions {
  spec?: string;
}

async function waitForServer(url: string, timeout = 60000): Promise<boolean> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(url);
      if (response.status === 200) {
        return true;
      }
    }
    catch {
      // Server not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return false;
}

async function run(options: ContractOptions): Promise<void> {
  const { spec } = options;
  let backend: ChildProcess | null = null;

  const cleanup = (): void => {
    if (backend && !backend.killed) {
      backend.kill('SIGTERM');
    }
  };

  process.on('SIGTERM', cleanup);
  process.on('SIGINT', cleanup);
  process.on('SIGHUP', cleanup);

  try {
    // Start the mocked backend
    consola.info('Starting mocked backend...');
    backend = spawn('pnpm', ['exec', 'tsx', 'scripts/start-mocked-backend.ts'], {
      stdio: ['pipe', 'inherit', 'inherit'],
    });

    // Wait for the backend to be ready
    const pingUrl = `${backendUrl}/api/1/ping`;
    consola.info(`Waiting for backend at ${pingUrl}...`);
    const ready = await waitForServer(pingUrl);

    if (!ready) {
      consola.error('Backend failed to start within timeout');
      cleanup();
      process.exit(1);
    }

    consola.success('Backend is ready');

    // Run the tests with the contract-specific vitest config
    const testArgs = ['run', '--config', 'vitest.config.contract.ts', '--coverage'];
    if (spec) {
      testArgs.push('--spec', `**/${spec}`);
    }

    consola.info('Running contract tests...');
    const testProcess = spawn('vitest', testArgs, {
      stdio: 'inherit',
    });

    const exitCode = await new Promise<number>((resolve) => {
      testProcess.on('exit', (code) => {
        resolve(code ?? 1);
      });
    });

    cleanup();

    if (exitCode === 0) {
      consola.success('Execution completed successfully');
    }
    else {
      consola.error('Tests failed');
    }

    process.exit(exitCode);
  }
  catch (error) {
    consola.error('Command execution failed', error);
    cleanup();
    process.exit(1);
  }
}

const cli = cac();

cli.command('', 'Contract tests - checks compliance between frontend and backend')
  .option('--spec <spec>', 'Specific spec to run')
  .action(async (options) => {
    await run({ spec: options.spec });
  });

cli.help();
cli.parse();
