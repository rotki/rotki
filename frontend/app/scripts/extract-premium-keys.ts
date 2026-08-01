/**
 * Extracts the translation keys used by the separately released premium bundle, so they are not
 * reported as unused in this repo.
 *
 * The premium components live in their own repository and resolve their messages against rotki's
 * i18n instance - they ship no locale files of their own. The keys were therefore silenced with a
 * blanket `premium_components.*` entry in the eslint ignore list, which also silenced the 60 keys
 * left over from premium screens retired several majors ago.
 *
 * Unlike the backend, that repository is not part of this checkout, so the generated file is the
 * source of truth and regeneration is opt-in: pass its path with `PREMIUM_COMPONENTS_PATH`, or keep
 * it as a sibling directory. When it cannot be found the check reports and exits cleanly rather
 * than failing, because CI has no premium checkout.
 *
 * rotki pins a components *major* (`COMPONENTS_VERSION` in rotkehlchen/premium/premium.py, and the
 * bundle filename derives from the premium package major), so the keys of the current major are the
 * complete set any supported rotki can request. Verified across every 15.x tag: the union is
 * identical to the tip, and identical again to 14.x.
 */

import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import process from 'node:process';
import consola from 'consola';

const GENERATED_FILE = '../premium-keys.generated.js';
/**
 * A lowercase-initial literal, dotted or not: the shape every message key in this project has.
 *
 * The dots are optional because en.json has one top-level string key (`theme_manager_lock`), and
 * requiring a dot made keys like it structurally invisible to this scan. Widening costs nothing in
 * precision: a literal only counts once it is intersected with en.json below, so ordinary strings
 * like 'div' are discarded anyway.
 */
const KEY_PATTERN = /['"`]([a-z]\w*(?:\.\w+)*)['"`]/g;

/** Directories that hold no source, or that would make the scan enormous. */
const SKIP_DIRS = new Set(['node_modules', 'dist', 'out', '.git', 'coverage', '.nuxt']);

function getGeneratedFilePath(): string {
  return join(import.meta.dirname, GENERATED_FILE);
}

/**
 * `PREMIUM_COMPONENTS_PATH` wins; otherwise try the layouts the repo is normally checked out in,
 * including a linked worktree, where the rotki root sits one level deeper than usual.
 *
 * Returning `undefined` makes the caller skip the check, which is right when no checkout exists (CI
 * has none). A path that was set explicitly is different: it says the check was meant to run, so a
 * typo there throws rather than skipping. Silently passing green is the worst outcome for a check
 * whose whole job is to stop premium keys being deleted while premium still uses them.
 */
export function findPremiumRepo(rotkiRoot: string): string | undefined {
  const fromEnv = process.env.PREMIUM_COMPONENTS_PATH;
  if (fromEnv) {
    if (!existsSync(fromEnv))
      throw new Error(`PREMIUM_COMPONENTS_PATH is set to '${fromEnv}', which does not exist`);

    return resolve(fromEnv);
  }

  const candidates = [
    resolve(rotkiRoot, '../premium-components'),
    resolve(rotkiRoot, '../../premium-components'),
  ];

  return candidates.find(candidate => existsSync(join(candidate, 'package.json')));
}

function getSourceFiles(dir: string): string[] {
  const files: string[] = [];

  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry))
      continue;

    const fullPath = join(dir, entry);
    if (statSync(fullPath).isDirectory())
      files.push(...getSourceFiles(fullPath));
    else if (entry.endsWith('.ts') || entry.endsWith('.vue') || entry.endsWith('.json'))
      files.push(fullPath);
  }

  return files;
}

/**
 * Every dotted string literal in the premium sources that names a message we ship.
 *
 * Deliberately not limited to `t(...)` arguments or to the `premium_components.*` namespace.
 * Premium also uses keys from ours - `net_worth_chart.*`, `common.*`, `statistics_graph_settings.*`.
 * Every key premium currently uses happens to be a direct `t()`/`$t()` argument, but keys can also
 * reach a registered rotki component as a plain prop, and a call-shape based scan would miss those.
 * Matching against en.json keeps the widened net precise: a literal only counts if it is a message
 * we actually have.
 *
 * Those shared keys are currently unreported only because rotki happens to use them too. Listing
 * them means retiring rotki's last use of one no longer silently makes it deletable.
 */
export function scanPremiumKeys(premiumRoot: string, messages: Set<string>): string[] {
  const keys = new Set<string>();

  for (const file of getSourceFiles(join(premiumRoot, 'packages'))) {
    for (const match of readFileSync(file, 'utf-8').matchAll(KEY_PATTERN)) {
      if (messages.has(match[1]))
        keys.add(match[1]);
    }
  }

  return [...keys].sort();
}

function generateFileContent(keys: string[]): string {
  const keyList = keys.map(key => `  '${key}',`).join('\n');
  return `/* eslint-disable */
/* prettier-ignore */
// Auto-generated file - DO NOT EDIT MANUALLY
// Generated by scripts/extract-premium-keys.ts
// To regenerate, run: pnpm run generate:premium-keys
// Consumed by eslint.config.js, which is plain ESM and cannot import TypeScript.

export const premiumComponentKeys = [
${keyList}
];
`;
}

export function readGeneratedKeys(): string[] {
  const path = getGeneratedFilePath();
  if (!existsSync(path))
    return [];

  const content = readFileSync(path, 'utf-8');
  const match = content.match(/export const premiumComponentKeys = \[([\S\s]*?)];/);
  return match ? Array.from(match[1].matchAll(/'([^']+)'/g), m => m[1]) : [];
}

function writeGeneratedFile(keys: string[]): void {
  writeFileSync(getGeneratedFilePath(), generateFileContent(keys), 'utf-8');
  consola.success(`Generated ${GENERATED_FILE} with ${keys.length} keys`);
}

/** Flattens the locale messages so keys can be looked up by their dotted path. */
function flattenKeys(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null)
    return [prefix];

  return Object.entries(value).flatMap(([key, nested]) =>
    flattenKeys(nested, prefix ? `${prefix}.${key}` : key));
}

/** Keys passed to `t()`/`$t()`. Narrower than KEY_PATTERN and not filtered against en.json, so it
 *  can report a key premium calls that we have no message for. */
const ANY_KEY_PATTERN = /\$?t\(\s*['"`]([a-z][\w.]*\.[\w.]+)['"`]/g;

function scanAllReferencedKeys(premiumRoot: string): string[] {
  const keys = new Set<string>();

  for (const file of getSourceFiles(join(premiumRoot, 'packages'))) {
    for (const match of readFileSync(file, 'utf-8').matchAll(ANY_KEY_PATTERN))
      keys.add(match[1]);
  }

  return [...keys].sort();
}

function readMessages(rotkiRoot: string): Set<string> {
  const localePath = join(rotkiRoot, 'frontend/app/src/locales/en.json');
  if (!existsSync(localePath)) {
    consola.error(`Cannot read ${localePath}`);
    process.exit(1);
  }

  return new Set(flattenKeys(JSON.parse(readFileSync(localePath, 'utf-8'))));
}

/**
 * Reports premium keys that rotki has no message for. Meant to be run from the premium repository
 * once it consumes rotki as a submodule: premium resolves its messages against rotki's i18n, so a
 * key premium adds without a matching en.json entry renders as the raw key path at runtime.
 */
function verify(premiumRoot: string, messages: Set<string>, keys: string[]): void {
  const referenced = scanAllReferencedKeys(premiumRoot);
  const missing = [...new Set([...keys, ...referenced])].filter(key => !messages.has(key)).sort();
  const generated = readGeneratedKeys();
  const unlisted = keys.filter(key => !generated.includes(key));

  consola.info(`${referenced.length} key(s) called through t()/$t(), ${keys.length} resolving against our messages`);

  if (missing.length > 0) {
    consola.error(`${missing.length} key(s) used by premium have no message in rotki's en.json:`);
    for (const key of missing)
      consola.error(`  ${key}`);
  }

  if (unlisted.length > 0) {
    consola.error(`${unlisted.length} key(s) are missing from ${GENERATED_FILE}:`);
    for (const key of unlisted)
      consola.error(`  ${key}`);
  }

  if (missing.length === 0 && unlisted.length === 0) {
    consola.success(`All ${keys.length} premium keys resolve against rotki`);
    return;
  }

  process.exit(1);
}

// CLI entry point
if (process.argv[1] === import.meta.filename) {
  const rotkiRoot = resolve(import.meta.dirname, '../../..');
  const shouldGenerate = process.argv.includes('--generate');
  const shouldVerify = process.argv.includes('--verify');

  let premiumRoot: string | undefined;
  try {
    premiumRoot = findPremiumRepo(rotkiRoot);
  }
  catch (error: unknown) {
    consola.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }

  if (premiumRoot === undefined) {
    consola.warn('premium-components checkout not found, skipping.');
    consola.warn('Set PREMIUM_COMPONENTS_PATH to enable this check.');
    process.exit(0);
  }

  consola.info(`Scanning ${premiumRoot}`);
  const messages = readMessages(rotkiRoot);
  const keys = scanPremiumKeys(premiumRoot, messages);
  consola.info(`Found ${keys.length} premium component keys`);

  if (shouldGenerate) {
    writeGeneratedFile(keys);
  }
  else if (shouldVerify) {
    verify(premiumRoot, messages, keys);
  }
  else {
    const existing = readGeneratedKeys();
    const added = keys.filter(key => !existing.includes(key));
    const removed = existing.filter(key => !keys.includes(key));

    if (added.length === 0 && removed.length === 0) {
      consola.success(`${GENERATED_FILE} is up to date`);
    }
    else {
      consola.error(`${GENERATED_FILE} is stale. Run: pnpm run generate:premium-keys`);
      for (const key of added)
        consola.error(`  + ${key}`);
      for (const key of removed)
        consola.error(`  - ${key}`);
      process.exit(1);
    }
  }
}
