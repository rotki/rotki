import { type ChildProcess, execSync, spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { ArgumentParser } from 'argparse';
import consola from 'consola';

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
  consola.success('✅ uv is installed');
}
else {
  consola.error('❌ uv not found - install from https://docs.astral.sh/uv/');
  process.exit(1);
}

const parser = new ArgumentParser({
  description: 'rotki backend',
});

parser.add_argument('--data', {
  help: 'data directory',
  type: 'str',
  required: true,
});

parser.add_argument('--logs', {
  help: 'logs directory',
  type: 'str',
  required: true,
});

parser.add_argument('--port', {
  help: 'listening port',
  required: true,
  type: 'int',
});

const { data: dataDir, logs: logDir, port } = parser.parse_args();

const args = [
  'run',
  '-m',
  'rotkehlchen',
  '--rest-api-port',
  port.toString(),
  '--api-cors',
  'http://localhost:*',
  '--data-dir',
  dataDir,
  '--logfile',
  `${path.join(logDir, 'rotki.log')}`,
  '--disable-task-manager',
];

consola.box('Starting backend');

let backend: ChildProcess;

process.on('SIGTERM', () => {
  if (backend)
    backend.kill();

  consola.info('Cleanup: complete\n');
  process.exit(0);
});

backend = spawn('uv', args, {
  stdio: [process.stdin, process.stdout, process.stderr],
  cwd: path.join('..', '..'),
});
