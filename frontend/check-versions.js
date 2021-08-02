const { execSync } = require('child_process');
const semver = require('semver');
const { engines } = require('rotki/package.json');
const requiredNodeVersion = engines.node;
if (!semver.satisfies(process.version, requiredNodeVersion)) {
  throw new Error(
    `${requiredNodeVersion} of node is required. The current node version ${process.version} does not satisfy the required version.`
  );
}

const npmVersion = `${execSync('npm --version')}`.trim();
const requiredNpmVersion = engines.npm;
if (!semver.satisfies(npmVersion, requiredNpmVersion)) {
  throw new Error(
    ` ${requiredNpmVersion} of npm is required. The current npm version ${npmVersion} does not satisfy the required version.`
  );
}
