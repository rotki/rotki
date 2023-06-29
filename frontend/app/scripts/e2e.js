#!/usr/bin/env node

const path = require('node:path');
const { execSync } = require('node:child_process');
const { startAndTest } = require('start-server-and-test');
const { ArgumentParser } = require('argparse');

const info = msg => {
  console.info(`\n\u001B[32m${msg}\u001B[0m\n`);
};

const parser = new ArgumentParser({
  description: 'e2e tests'
});
parser.add_argument('--ci', {
  help: 'will run e2e tests in headless mode',
  action: 'store_true'
});
parser.add_argument('--spec', { help: 'specific spec to run ' });
parser.add_argument('--browser', {
  help: 'specify browser to use when running '
});
const { ci, spec, browser } = parser.parse_args();

require('dotenv').config({
  path: path.join(process.cwd(), '.env.e2e')
});

const frontendPort = 22230;

const backendUrl = process.env.VITE_BACKEND_URL;
process.env.CYPRESS_BACKEND_URL = backendUrl;

// pnpm will cause the commands to exit with
// ELIFECYCLE Command failed.
// If we find away around this we should change to pnpm.
const frontendCmd = ci ? 'vite preview' : 'node scripts/serve.js --web';
const services = [
  {
    start: 'node scripts/start-backend.js',
    url: `${backendUrl}/api/1/ping`
  },
  {
    start: `${frontendCmd} --port ${frontendPort}`,
    url: `http://localhost:${frontendPort}`
  }
];

const testCmd = ci ? 'pnpm run cypress:run' : 'pnpm run cypress:open';

let test = testCmd;
if (spec) {
  test += ` --spec **/${spec}`;
}

if (browser) {
  test += ` --browser ${browser}`;
}

if (ci) {
  info('Building frontend');
  const start = Date.now();
  execSync('pnpm run build --mode e2e');
  info(`Build complete (${Date.now() - start} ms)`);
}

startAndTest({
  services,
  test,
  namedArguments: { expect: 200 }
})
  .then(() => {
    info('Execution completed successfully');
    process.exit(0);
  })
  .catch(() => {
    console.error('Command execution failed');
    process.exit(1);
  });
