import { type ChildProcess, execSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import consola from 'consola';

if (!(process.env.CI || process.env.VIRTUAL_ENV)) {
  consola.error('Not CI or VIRTUAL_ENV');
  process.exit(1);
}

/**
 * Synchronously check if uv is installed
 * @returns boolean - true if uv is installed, false otherwise
 */
function isUvInstalledSync(): boolean {
  try {
    execSync('uv --version', { stdio: 'ignore' });
    return true;
  }
  catch {
    return false;
  }
}

if (isUvInstalledSync()) {
  consola.success('uv is installed');
}
else {
  consola.error('uv not found - install from https://docs.astral.sh/uv/');
  process.exit(1);
}

const testDir = path.join(process.cwd(), '.contract');
const dataDir = path.join(testDir, 'data');

consola.info(`Using ${dataDir} to start tests`);

function cleanupData(): void {
  if (!fs.existsSync(dataDir))
    return;

  const contents = fs.readdirSync(dataDir);
  for (const name of contents) {
    if (['images', 'global'].includes(name))
      continue;

    const currentPath = path.join(dataDir, name);
    if (fs.statSync(currentPath).isDirectory())
      fs.rmSync(currentPath, { recursive: true });
  }
}

if (!fs.existsSync(dataDir))
  fs.mkdirSync(dataDir, { recursive: true });
else
  cleanupData();

const logDir = path.join(testDir, 'logs');

consola.info(`Using ${logDir} to output backend logs`);

if (!fs.existsSync(logDir))
  fs.mkdirSync(logDir, { recursive: true });

const args = [
  'run',
  '-m',
  'rotkehlchen_mock',
  '--rest-api-port',
  '22221',
  '--api-cors',
  'http://127.0.0.1:*',
  '--data-dir',
  dataDir,
  '--logfile',
  path.join(logDir, 'contract.log'),
];

let backend: ChildProcess;
let isCleaningUp = false;

function cleanup(signal: string): void {
  if (isCleaningUp)
    return;
  isCleaningUp = true;

  consola.info(`Received ${signal}, cleaning up...`);
  if (backend && !backend.killed) {
    backend.kill('SIGTERM');
    // Give it a moment to die gracefully, then force kill
    setTimeout(() => {
      if (backend && !backend.killed) {
        backend.kill('SIGKILL');
      }
    }, 5000);
  }

  cleanupData();
  consola.info('Cleanup: complete');
}

process.on('SIGTERM', () => cleanup('SIGTERM'));
process.on('SIGINT', () => cleanup('SIGINT'));
process.on('SIGHUP', () => cleanup('SIGHUP'));

consola.box('Starting mocked backend');

backend = spawn('uv', args, {
  stdio: [process.stdin, process.stdout, process.stderr],
  cwd: path.join('..', '..'),
});

backend.on('exit', (code) => {
  consola.info(`Mocked backend exited with code ${code}`);
  process.exit(code ?? 0);
});
