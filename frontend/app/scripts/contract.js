#!/usr/bin/env node

const path = require('node:path');
const { startAndTest } = require('start-server-and-test');
const { ArgumentParser } = require('argparse');

function info(msg) {
  console.info(`\n\u001B[32m${msg}\u001B[0m\n`);
};

const parser = new ArgumentParser({
  description: 'contract tests, this checks compliance between frontend and backend',
});
parser.add_argument('--spec', { help: 'specific spec to run ' });

const { spec } = parser.parse_args();

require('dotenv').config({
  path: path.join(process.cwd(), '.env.contract'),
});

const backendUrl = process.env.VITE_BACKEND_URL;

const services = [
  {
    start: 'node scripts/start-mocked-backend.js',
    url: `${backendUrl}/api/1/ping`,
  },
];

const testCmd = 'cross-env TZ=UTC VITE_TEST=true vitest run --dir tests/contract --coverage';

let test = testCmd;
if (spec)
  test += ` --spec **/${spec}`;

async function run() {
  startAndTest({
    services,
    test,
    namedArguments: { expect: 200 },
  })
    .then(() => {
      info('Execution completed successfully');
      process.exit(0);
    })
    .catch(() => {
      console.error('Command execution failed');
      process.exit(1);
    });
}

// re-evaluate after moving to mjs or ts
// eslint-disable-next-line unicorn/prefer-top-level-await
run();
