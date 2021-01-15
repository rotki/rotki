const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const tmpDir = os.tmpdir();
let tempPath = path.join(tmpDir, 'rotki');

process.stdout.write(`Using ${tempPath} to start tests`);

if (!fs.existsSync(tempPath)) {
  fs.mkdirSync(tempPath);
} else {
  const contents = fs.readdirSync(tempPath);
  contents.forEach(name => {
    const currentPath = path.join(tempPath, name);
    if (fs.statSync(currentPath).isDirectory()) {
      fs.rmdirSync(currentPath, { recursive: true });
    }
  });
}

const args = [
  '-m',
  'rotkehlchen',
  '--api-port',
  '22221',
  '--api-cors',
  'http://localhost:*',
  '--data-dir',
  tempPath
];

spawn('python', args, {
  stdio: [process.stdin, process.stdout, process.stderr]
});
