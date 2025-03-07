import { type ChildProcess, spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { ArgumentParser } from 'argparse';
import consola from 'consola';

if (!(process.env.CI || process.env.VIRTUAL_ENV)) {
  consola.error('Not CI or VIRTUAL_ENV');
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

let backend: ChildProcess;

process.on('SIGTERM', () => {
  if (backend)
    backend.kill();

  consola.info('Cleanup: complete\n');
  process.exit(0);
});

backend = spawn('python', args, {
  stdio: [process.stdin, process.stdout, process.stderr],
  cwd: path.join('..', '..'),
});
