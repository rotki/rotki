#!/usr/bin/env node

import path from 'node:path';
import process from 'node:process';
import { ArgumentParser } from 'argparse';
import { config } from 'dotenv';
import { startAndTest } from 'start-server-and-test';

function info(msg) {
  console.info(`\n\u001B[32m${msg}\u001B[0m\n`);
}

const parser = new ArgumentParser({
  description: 'contract tests, this checks compliance between frontend and backend',
});
parser.add_argument('--spec', { help: 'specific spec to run ' });

const { spec } = parser.parse_args();

config({
  path: path.join(process.cwd(), '.env.contract'),
});

const backendUrl = process.env.VITE_BACKEND_URL;

const services = [
  {
    start: 'node scripts/start-mocked-backend.js',
    url: `${backendUrl}/api/1/ping`,
  },
];

const testCmd = 'vitest run --dir tests/contract --coverage';

let test = testCmd;
if (spec)
  test += ` --spec **/${spec}`;

async function run() {
  try {
    await startAndTest({
      services,
      test,
      namedArguments: { expect: 200 },
    });
    info('Execution completed successfully');
    process.exit(0);
  }
  catch (error) {
    console.error('Command execution failed', error);
    process.exit(1);
  }
}

// re-evaluate after moving to mjs or ts
// eslint-disable-next-line unicorn/prefer-top-level-await
run();
