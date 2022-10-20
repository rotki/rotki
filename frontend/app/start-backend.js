const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

if (!(process.env.CI || process.env.VIRTUAL_ENV)) {
  process.stdout.write(`\x1b[31mError\x1b[0m: Not CI or VIRTUAL_ENV\n\n`);
  process.exit(1);
}

const tmpDir = process.env.CI ? os.homedir() : os.tmpdir();
let tempPath = path.join(tmpDir, 'rotki-e2e');

process.stdout.write(`Using ${tempPath} to start tests\n`);

if (!fs.existsSync(tempPath)) {
  fs.mkdirSync(tempPath);
} else {
  const contents = fs.readdirSync(tempPath);
  for (const name of contents) {
    if (['icons', 'price_history', 'global_data'].includes(name)) {
      continue;
    }

    const currentPath = path.join(tempPath, name);
    if (fs.statSync(currentPath).isDirectory()) {
      fs.rmSync(currentPath, { recursive: true });
    }
  }
}

const logDir = path.join(os.homedir(), 'rotki-e2e-logs');

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
  tempPath,
  '--logfile',
  `${path.join(logDir, 'rotkehlchen-e2e.log')}`
];

spawn('python', args, {
  stdio: [process.stdin, process.stdout, process.stderr]
});
