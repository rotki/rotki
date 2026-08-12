import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import consola from 'consola';

/**
 * Gives an unsharded `pnpm test:e2e` the pristine global database a shard gets from the
 * template built in `e2e-shards.ts`.
 *
 * Manually-input prices live in the global database. Unlike the per-run users it is reused,
 * so a run that dies before its cleanup leaves its rows behind, and they accumulate:
 * `price-manager.spec.ts` adds a row and asserts it is visible, but the table is
 * date-descending and pages at ten rows, so past a certain count the new row lands on page
 * two and the spec fails for a reason that has nothing to do with the code.
 *
 * This runs as a step of its own rather than from `playwright.config.ts`, because the config
 * is imported by the test helpers too (`seed-db.ts` reads `dataDir` from it), so anything it
 * does at module load runs again inside every worker process - which for this would mean
 * replacing the database out from under the backend that already has it open, mid-run.
 *
 * Self-contained on purpose: it is run by plain `node`, which strips types but resolves
 * specifiers literally, and the repo forbids `.ts` import specifiers. The one thing it shares
 * with `e2e-shards.ts` is the packaged database path, which is the backend's own
 * (`globaldb/handler.py` copies it into a fresh data directory).
 */
const appDir = path.resolve(import.meta.dirname, '..');
const packagedGlobalDb = path.join(appDir, '..', '..', 'rotkehlchen', 'data', 'global.db');
// `.e2e` is resolved from the cwd exactly as `playwright.config.ts` resolves it, so a
// worktree still gets its own directory.
const dataDir = path.join(process.cwd(), '.e2e', 'data');

if (!fs.existsSync(packagedGlobalDb)) {
  throw new Error(`Packaged global database not found at ${packagedGlobalDb}`);
}

// Only the global database is replaced. Users are created per run anyway, and the icon cache
// beside them is worth keeping - it is a pure cache, but a cold one costs minutes.
const globalDir = path.join(dataDir, 'global');
fs.rmSync(globalDir, { recursive: true, force: true });
fs.mkdirSync(globalDir, { recursive: true });

const result = spawnSync('cp', ['-a', '--reflink=auto', packagedGlobalDb, path.join(globalDir, 'global.db')], {
  stdio: 'inherit',
});

if (result.status !== 0) {
  throw new Error(`Failed to copy ${packagedGlobalDb} into ${globalDir}`);
}

consola.success(`Reset the global database in ${dataDir}`);
