const { execSync } = require('node:child_process');
const semver = require('semver');
const { engines } = require('../package.json');

const pnpmVersion = `${execSync('pnpm --version')}`.trim();
const requiredPnpmVersion = engines.pnpm;
const requiredNodeVersion = engines.node;

const error = e => `\u001B[40m\u001B[31m${e}\u001B[0m`;
const version = version => `\u001B[33m\u001B[40m${version}\u001B[0m`;

if (!semver.satisfies(pnpmVersion, requiredPnpmVersion)) {
  console.error(
    `${error(
      'ERROR!'
    )} ${requiredPnpmVersion} of pnpm is required. The current pnpm version ${version(
      pnpmVersion
    )} does not satisfy the required version.\n\n`
  );
  process.exit(1);
}

if (!semver.satisfies(process.version, requiredNodeVersion)) {
  console.error(
    `${error(
      'ERROR!'
    )} ${requiredNodeVersion} of node is required. The current node version ${version(
      process.version
    )} does not satisfy the required version.\n\n`
  );
  process.exit(1);
}
