import { type ChildProcess, spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { ArgumentParser } from 'argparse';
import consola from 'consola';

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
  `--data-directory=${dataDir}`,
  `--logfile-path=${path.join(logDir, 'colibri.log')}`,
  `--port=${port}`,
  `--api-cors=http://localhost:*`,
];

let backend: ChildProcess;

process.on('SIGTERM', () => {
  if (backend)
    backend.kill();

  consola.info('Cleanup: complete\n');
  process.exit(0);
});

const workDir = path.join(import.meta.dirname, '..', '..', '..', 'colibri');
consola.info(`Starting Colibri in ${workDir}`);

backend = spawn('cargo run -- ', args, {
  stdio: [process.stdin, process.stdout, process.stderr],
  shell: true,
  cwd: workDir,
});
