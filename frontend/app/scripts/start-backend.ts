import { type ChildProcess, execSync, spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
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

interface BackendOptions {
  data: string;
  logs: string;
  port: number;
}

function startBackend(options: BackendOptions): void {
  const { data: dataDir, logs: logDir, port } = options;

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
  }

  process.on('SIGTERM', () => cleanup('SIGTERM'));
  process.on('SIGINT', () => cleanup('SIGINT'));
  process.on('SIGHUP', () => cleanup('SIGHUP'));

  backend = spawn('uv', args, {
    stdio: [process.stdin, process.stdout, process.stderr],
    cwd: path.join('..', '..'),
  });

  backend.on('exit', (code) => {
    consola.info(`Backend exited with code ${code}`);
    process.exit(code ?? 0);
  });
}

const cli = cac();

cli.command('', 'Start rotki backend')
  .option('--data <dir>', 'Data directory')
  .option('--logs <dir>', 'Logs directory')
  .option('--port <port>', 'Listening port')
  .action((options) => {
    if (!options.data || !options.logs || !options.port) {
      consola.error('Missing required options: --data, --logs, --port');
      process.exit(1);
    }
    startBackend({
      data: options.data,
      logs: options.logs,
      port: Number(options.port),
    });
  });

cli.help();
cli.parse();
