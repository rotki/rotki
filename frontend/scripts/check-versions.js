import { execSync } from 'node:child_process';
import process from 'node:process';
import semver from 'semver';
import fs from 'node:fs';

const pnpmVersion = execSync('pnpm --version').toString().trim();
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const requiredPnpmVersion = pkg.engines.pnpm;
const requiredNodeVersion = pkg.engines.node;

const error = e => `\u001B[40m\u001B[31m${e}\u001B[0m`;
const version = version => `\u001B[33m\u001B[40m${version}\u001B[0m`;

if (!semver.satisfies(pnpmVersion, requiredPnpmVersion)) {
  console.error(
    `${error('ERROR!')} ${requiredPnpmVersion} of pnpm is required. The current pnpm version ${version(
      pnpmVersion,
    )} does not satisfy the required version.\n\n`,
  );
  process.exit(1);
}

if (!semver.satisfies(process.version, requiredNodeVersion)) {
  console.error(
    `${error('ERROR!')} ${requiredNodeVersion} of node is required. The current node version ${version(
      process.version,
    )} does not satisfy the required version.\n\n`,
  );
  process.exit(1);
}
