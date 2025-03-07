import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

if (!(process.env.CI || process.env.VIRTUAL_ENV)) {
  process.stdout.write(`\u001B[31mError\u001B[0m: Not CI or VIRTUAL_ENV\n\n`);
  process.exit(1);
}

const testDir = path.join(process.cwd(), '.contract');
const dataDir = path.join(testDir, 'data');

process.stdout.write(`Using ${dataDir} to start tests\n`);

function cleanupData() {
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
else cleanupData();

const logDir = path.join(testDir, 'logs');

process.stdout.write(`Using ${logDir} to output backend logs\n`);

if (!fs.existsSync(logDir))
  fs.mkdirSync(logDir, { recursive: true });

const args = [
  '-m',
  'rotkehlchen_mock',
  '--rest-api-port',
  '22221',
  '--websockets-api-port',
  '22222',
  '--api-cors',
  'http://localhost:*',
  '--data-dir',
  dataDir,
  '--logfile',
  `${path.join(logDir, 'contract.log')}`,
];

let backend;

process.on('SIGTERM', () => {
  if (backend)
    backend.kill();

  cleanupData();
  process.stdout.write('Cleanup: complete\n');
  process.exit(0);
});

backend = spawn('python', args, {
  stdio: [process.stdin, process.stdout, process.stderr],
  cwd: path.join('..', '..'),
});
