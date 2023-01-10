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
const { ci, spec } = parser.parse_args();

require('dotenv').config({
  path: path.join(process.cwd(), '.env.e2e')
});

// pnpm will cause the commands to exit with
// ELIFECYCLE Command failed.
// If we find away around this we should change to pnpm.
const services = [
  {
    start: 'npm run serve:backend',
    url: 'http://localhost:22221/api/1/ping'
  },
  {
    start: 'npm run serve',
    url: 'http://localhost:8080'
  }
];

const testCmd = ci ? 'npm run cypress:run' : 'npm run cypress:open';

let test = testCmd;
if (spec) {
  test += ` --spec **/${spec}`;
}
startAndTest({
  services,
  test,
  namedArguments: { expect: 200 }
});
