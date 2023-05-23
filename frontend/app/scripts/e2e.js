#!/usr/bin/env node

const path = require('node:path');
const { startAndTest } = require('start-server-and-test');
const { ArgumentParser } = require('argparse');

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
const services = [
  {
    start: 'node scripts/start-backend.js',
    url: `${backendUrl}/api/1/ping`
  },
  {
    start: `node scripts/serve.js --web --port ${frontendPort}`,
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

startAndTest({
  services,
  test,
  namedArguments: { expect: 200 }
})
  .then(() => {
    console.info('Execution completed successfully');
    process.exit(0);
  })
  .catch(() => {
    console.error('Command execution failed');
    process.exit(1);
  });
