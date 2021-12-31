const { execSync } = require('child_process');
const semver = require('semver');
const { engines } = require('./package.json');

const npmVersion = `${execSync('npm --version')}`.trim();
const requiredNpmVersion = engines.npm;
const requiredNodeVersion = engines.node;

const error = (e) => `\x1b[40m\x1b[31m${e}\x1b[0m`;
const version = (version) => `\x1b[33m\x1b[40m${version}\x1b[0m`;

if (!semver.satisfies(npmVersion, requiredNpmVersion)) {
  console.error(`${error('ERROR!')} ${requiredNpmVersion} of npm is required. The current npm version ${version(npmVersion)} does not satisfy the required version.\n\n`)
  process.exit(1)
}

if (!semver.satisfies(process.version, requiredNodeVersion)) {
  console.error(`${error('ERROR!')} ${requiredNodeVersion} of node is required. The current node version ${version(process.version)} does not satisfy the required version.\n\n`);
  process.exit(1)
}
