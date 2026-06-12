import { type ChildProcess, spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';

/**
 * Contract test runner (measurement framework §5.1).
 *
 * Builds a golden user profile (tools/scenarios), boots the real backend on
 * it, then runs the contract vitest suite (vitest.contract.config.ts) with
 * the backend url and the profile's expected values in the environment.
 */

const appDir = path.resolve(import.meta.dirname, '..');
const repoRoot = path.resolve(appDir, '..', '..');

async function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (address === null || typeof address === 'string') {
        reject(new Error('could not allocate a port'));
        return;
      }
      server.close(() => resolve(address.port));
    });
  });
}

function buildProfile(profile: string, dataDir: string): void {
  consola.start(`Building golden profile '${profile}'`);
  const result = spawnSync(
    'uv',
    ['run', 'python', '-m', 'tools.scenarios', 'build', '--profile', profile, '--output', dataDir],
    { cwd: repoRoot, encoding: 'utf8' },
  );
  if (result.status !== 0)
    throw new Error(`profile build failed:\n${result.stderr}\n${result.stdout}`);
  consola.success(`Profile ready at ${dataDir}`);
}

async function startBackend(dataDir: string, logDir: string, port: number): Promise<ChildProcess> {
  fs.mkdirSync(logDir, { recursive: true });
  const log = fs.openSync(path.join(logDir, 'stdout.log'), 'a');
  const backend = spawn(
    'uv',
    [
      'run',
      'python',
      '-m',
      'rotkehlchen',
      '--rest-api-port',
      port.toString(),
      '--api-cors',
      'http://localhost:*',
      '--data-dir',
      dataDir,
      '--logfile',
      path.join(logDir, 'rotki.log'),
    ],
    { cwd: repoRoot, stdio: ['ignore', log, log] },
  );

  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (backend.exitCode !== null)
      throw new Error(`backend exited with code ${backend.exitCode}; see ${logDir}`);
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/1/ping`);
      if (response.ok) {
        consola.success(`Backend answering on port ${port}`);
        return backend;
      }
    }
    catch {
      // not up yet
    }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  backend.kill('SIGKILL');
  throw new Error('backend did not answer ping within 120s');
}

async function main(profile: string): Promise<void> {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'rotki-contract-'));
  const dataDir = path.join(workDir, 'data');
  const logDir = path.join(workDir, 'logs');
  let backend: ChildProcess | undefined;
  let status = 1;

  try {
    buildProfile(profile, dataDir);
    const expected = fs.readFileSync(
      path.join(dataDir, 'users', profile, 'expected.json'),
      'utf8',
    );
    const port = await freePort();
    backend = await startBackend(dataDir, logDir, port);

    consola.start('Running contract tests');
    const vitest = spawnSync(
      'pnpm',
      ['exec', 'vitest', 'run', '--config', 'vitest.contract.config.ts'],
      {
        cwd: appDir,
        env: {
          ...process.env,
          CONTRACT_BACKEND_URL: `http://127.0.0.1:${port}`,
          CONTRACT_EXPECTED: expected,
          CONTRACT_USERNAME: profile,
        },
        stdio: 'inherit',
      },
    );
    status = vitest.status ?? 1;
  }
  finally {
    if (backend && backend.exitCode === null) {
      backend.kill('SIGTERM');
      await new Promise(resolve => setTimeout(resolve, 2000));
      if (backend.exitCode === null)
        backend.kill('SIGKILL');
    }
    if (status !== 0 && fs.existsSync(logDir)) {
      // keep the backend logs out of the doomed tmpdir so CI can upload them
      const preservedLogDir = path.join(appDir, '.contract', 'logs');
      fs.rmSync(preservedLogDir, { force: true, recursive: true });
      fs.cpSync(logDir, preservedLogDir, { recursive: true });
      consola.info(`Backend logs preserved at ${preservedLogDir}`);
    }
    fs.rmSync(workDir, { force: true, recursive: true });
  }
  process.exit(status);
}

const cli = cac();

cli.command('', 'Run the API contract tests against a live backend')
  .option('--profile <name>', 'Golden profile to boot', { default: 'small' })
  .action(async (options: { profile: string }) => {
    await main(options.profile);
  });

cli.help();
cli.parse();
