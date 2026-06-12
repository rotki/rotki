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
 * Builds a golden user profile (tools/scenarios), boots the mock for the
 * backend's external services on the profile's chain state, boots the real
 * backend through the bench launcher (which redirects all external HTTP to
 * the mock — zero egress), points its rpc nodes at the mock, then runs the
 * contract vitest suite (vitest.contract.config.ts) with the backend url
 * and the profile's expected values in the environment.
 */

const appDir = path.resolve(import.meta.dirname, '..');
const repoRoot = path.resolve(appDir, '..', '..');
const launcher = path.join(repoRoot, 'tools', 'bench', 'launch_backend.py');

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

async function startMock(dataDir: string): Promise<{ process: ChildProcess; url: string }> {
  const mock = spawn(
    'uv',
    ['run', 'python', '-m', 'tools.bench.mockserver', '--state', path.join(dataDir, 'chain_state.json')],
    { cwd: repoRoot, stdio: ['ignore', 'pipe', 'inherit'] },
  );
  const url = await new Promise<string>((resolve, reject) => {
    let buffer = '';
    const timer = setTimeout(() => {
      reject(new Error('mock server did not announce its url within 60s'));
    }, 60_000);
    mock.stdout?.on('data', (chunk: { toString: () => string }) => {
      buffer += chunk.toString();
      const match = /MOCK_URL=(\S+)/.exec(buffer);
      if (match) {
        clearTimeout(timer);
        resolve(match[1]);
      }
    });
    mock.once('exit', (code) => {
      clearTimeout(timer);
      reject(new Error(`mock server exited with code ${code}`));
    });
  });
  consola.success(`External services mock answering on ${url}`);
  return { process: mock, url };
}

async function unlockUser(backendUrl: string, username: string): Promise<void> {
  const response = await fetch(`${backendUrl}/api/1/users/${username}`, {
    body: JSON.stringify({
      password: process.env.CONTRACT_PASSWORD ?? '1234',
      resume_from_backup: false,
      sync_approval: 'no',
    }),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });
  if (!response.ok) {
    const body = await response.text();
    if (!body.includes('logged'))
      throw new Error(`failed to unlock user ${username}: ${response.status} ${body}`);
  }
}

/**
 * Replace the chain's rpc nodes with the mock (same approach as the bench
 * harness and the e2e helper): delete all defaults, register the mock as
 * the only node.
 */
async function useMockRpcNodes(backendUrl: string, mockUrl: string): Promise<void> {
  const nodesUrl = `${backendUrl}/api/1/blockchains/eth/nodes`;
  const headers = { 'Content-Type': 'application/json' };
  const nodes = await (await fetch(nodesUrl)).json();
  for (const node of nodes.result ?? []) {
    if (node.identifier) {
      await fetch(nodesUrl, {
        body: JSON.stringify({ identifier: node.identifier }),
        headers,
        method: 'DELETE',
      });
    }
  }
  const response = await fetch(nodesUrl, {
    body: JSON.stringify({
      active: true,
      endpoint: `${mockUrl}/rpc/1`,
      name: 'contract-mock',
      owned: true,
      weight: '1.00',
    }),
    headers,
    method: 'PUT',
  });
  if (!response.ok)
    throw new Error(`failed to register the mock rpc node: ${await response.text()}`);
}

/**
 * Nothing can leave the machine (the launcher redirects everything to the
 * mock), so this is about answer quality: unhandled rpc methods mean the
 * chain pipeline got wrong answers and fail the run; other unmocked
 * services (background task traffic) are reported for mock backfilling.
 */
async function checkMockEgress(mockUrl: string): Promise<boolean> {
  const stats = await (await fetch(`${mockUrl}/__mock__/stats`)).json();
  const unhandled = Object.entries(stats.unhandled ?? {});
  if (unhandled.length === 0)
    return true;
  consola.warn(`Unmocked external calls (answered with 404):\n${
    unhandled.map(([key, count]) => `  ${String(count)}x ${key}`).join('\n')}`);
  const rpcMisses = unhandled.filter(([key]) => key.startsWith('rpc:'));
  if (rpcMisses.length > 0) {
    consola.error('Unhandled rpc methods mean the chain answers were wrong; failing the run.');
    return false;
  }
  return true;
}

async function startBackend(dataDir: string, logDir: string, port: number, mockUrl: string): Promise<ChildProcess> {
  fs.mkdirSync(logDir, { recursive: true });
  const log = fs.openSync(path.join(logDir, 'stdout.log'), 'a');
  const backend = spawn(
    'uv',
    [
      'run',
      'python',
      launcher,
      '--rest-api-port',
      port.toString(),
      '--api-cors',
      'http://localhost:*',
      '--data-dir',
      dataDir,
      '--logfile',
      path.join(logDir, 'rotki.log'),
    ],
    {
      cwd: repoRoot,
      env: { ...process.env, ROTKI_BENCH_MOCK_URL: mockUrl },
      stdio: ['ignore', log, log],
    },
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

function runVitest(profile: string, backendUrl: string, expected: string): number {
  consola.start('Running contract tests');
  const vitest = spawnSync(
    'pnpm',
    ['exec', 'vitest', 'run', '--config', 'vitest.contract.config.ts'],
    {
      cwd: appDir,
      env: {
        ...process.env,
        CONTRACT_BACKEND_URL: backendUrl,
        CONTRACT_EXPECTED: expected,
        CONTRACT_USERNAME: profile,
      },
      stdio: 'inherit',
    },
  );
  return vitest.status ?? 1;
}

async function main(profile: string): Promise<void> {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'rotki-contract-'));
  const dataDir = path.join(workDir, 'data');
  const logDir = path.join(workDir, 'logs');
  let backend: ChildProcess | undefined;
  let mock: { process: ChildProcess; url: string } | undefined;
  let status = 1;

  try {
    buildProfile(profile, dataDir);
    const expected = fs.readFileSync(
      path.join(dataDir, 'users', profile, 'expected.json'),
      'utf8',
    );
    const port = await freePort();
    mock = await startMock(dataDir);
    backend = await startBackend(dataDir, logDir, port, mock.url);
    const backendUrl = `http://127.0.0.1:${port}`;
    await unlockUser(backendUrl, profile);
    await useMockRpcNodes(backendUrl, mock.url);

    status = runVitest(profile, backendUrl, expected);
    if (status === 0 && !(await checkMockEgress(mock.url)))
      status = 1;
  }
  finally {
    if (backend && backend.exitCode === null) {
      backend.kill('SIGTERM');
      await new Promise(resolve => setTimeout(resolve, 2000));
      if (backend.exitCode === null)
        backend.kill('SIGKILL');
    }
    if (mock && mock.process.exitCode === null)
      mock.process.kill('SIGTERM');
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
