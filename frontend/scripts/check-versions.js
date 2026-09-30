import { execSync } from 'node:child_process';
import process from 'node:process';
import pkg from '../package.json' with { type: 'json' };

/**
 * Checks a version against a space-separated comparator list such as `>=24 <25`.
 *
 * @remarks
 * pnpm runs this as the root `preinstall`, before any dependency is installed,
 * so it must not import packages; the `engines` ranges only use these comparators.
 */
function satisfies(version, range) {
  const toParts = value => value.replace(/^v/, '').split('.').map(part => Number.parseInt(part, 10) || 0);
  const compare = (a, b) => {
    for (let i = 0; i < 3; i++) {
      const diff = (a[i] ?? 0) - (b[i] ?? 0);
      if (diff !== 0)
        return diff;
    }
    return 0;
  };
  const current = toParts(version);
  return range.trim().split(/\s+/).every((comparator) => {
    const [, operator, target] = /^(>=|<=|>|<|=)?(.+)$/.exec(comparator);
    const result = compare(current, toParts(target));
    switch (operator) {
      case '>=': return result >= 0;
      case '<=': return result <= 0;
      case '>': return result > 0;
      case '<': return result < 0;
      default: return result === 0;
    }
  });
}

const pnpmVersion = `${execSync('pnpm --version')}`.trim();
const requiredPnpmVersion = pkg.engines.pnpm;
const requiredNodeVersion = pkg.engines.node;

const error = e => `\u001B[40m\u001B[31m${e}\u001B[0m`;
const version = version => `\u001B[33m\u001B[40m${version}\u001B[0m`;

if (!satisfies(pnpmVersion, requiredPnpmVersion)) {
  console.error(
    `${error('ERROR!')} ${requiredPnpmVersion} of pnpm is required. The current pnpm version ${version(
      pnpmVersion,
    )} does not satisfy the required version.\n\n`,
  );
  process.exit(1);
}

if (!satisfies(process.version, requiredNodeVersion)) {
  console.error(
    `${error('ERROR!')} ${requiredNodeVersion} of node is required. The current node version ${version(
      process.version,
    )} does not satisfy the required version.\n\n`,
  );
  process.exit(1);
}
