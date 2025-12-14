import { type ChildProcess, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';

interface ColibriOptions {
  data: string;
  logs: string;
  port: number;
}

function startColibri(options: ColibriOptions): void {
  const { data: dataDir, logs: logDir, port } = options;

  const args = [
    `--data-directory=${dataDir}`,
    `--logfile-path=${path.join(logDir, 'colibri.log')}`,
    `--port=${port}`,
    `--api-cors=http://localhost:*`,
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
  }

  process.on('SIGTERM', () => cleanup('SIGTERM'));
  process.on('SIGINT', () => cleanup('SIGINT'));
  process.on('SIGHUP', () => cleanup('SIGHUP'));

  const workDir = path.join(import.meta.dirname, '..', '..', '..', 'colibri');
  const binaryPath = path.join(workDir, 'target', 'release', 'colibri');
  const useBinary = process.env.CI && fs.existsSync(binaryPath);

  const command = useBinary ? binaryPath : 'cargo run --';
  consola.info(`Starting Colibri in ${workDir} using ${useBinary ? 'pre-built binary' : 'cargo run'}`);

  backend = spawn(command, args, {
    stdio: [process.stdin, process.stdout, process.stderr],
    shell: true,
    cwd: workDir,
  });

  backend.on('exit', (code) => {
    consola.info(`Colibri exited with code ${code}`);
    process.exit(code ?? 0);
  });
}

const cli = cac();

cli.command('', 'Start Colibri service')
  .option('--data <dir>', 'Data directory')
  .option('--logs <dir>', 'Logs directory')
  .option('--port <port>', 'Listening port')
  .action((options) => {
    if (!options.data || !options.logs || !options.port) {
      consola.error('Missing required options: --data, --logs, --port');
      process.exit(1);
    }
    startColibri({
      data: options.data,
      logs: options.logs,
      port: Number(options.port),
    });
  });

cli.help();
cli.parse();
