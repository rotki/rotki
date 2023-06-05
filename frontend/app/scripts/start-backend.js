const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

if (!(process.env.CI || process.env.VIRTUAL_ENV)) {
  process.stdout.write(`\u001B[31mError\u001B[0m: Not CI or VIRTUAL_ENV\n\n`);
  process.exit(1);
}

const testDir = path.join(process.cwd(), '.e2e');
const dataDir = path.join(testDir, 'data');

process.stdout.write(`Using ${dataDir} to start tests\n`);

const cleanupData = () => {
  const contents = fs.readdirSync(dataDir);
  for (const name of contents) {
    if (['icons', 'price_history', 'global_data'].includes(name)) {
      continue;
    }

    const currentPath = path.join(dataDir, name);
    if (fs.statSync(currentPath).isDirectory()) {
      fs.rmSync(currentPath, { recursive: true });
    }
  }
};

if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
} else {
  cleanupData();
}

const logDir = path.join(testDir, 'logs');

process.stdout.write(`Using ${logDir} to output backend logs\n`);

if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir);
}

const args = [
  '-m',
  'rotkehlchen',
  '--rest-api-port',
  '22221',
  '--websockets-api-port',
  '22222',
  '--api-cors',
  'http://localhost:*',
  '--data-dir',
  dataDir,
  '--logfile',
  `${path.join(logDir, 'e2e.log')}`
];

let backend;

process.on('SIGTERM', () => {
  if (backend) {
    backend.kill();
  }
  cleanupData();
  process.stdout.write('Cleanup: complete\n');
  process.exit(0);
});

backend = spawn('python', args, {
  stdio: [process.stdin, process.stdout, process.stderr]
});
