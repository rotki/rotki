import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { availableParallelism, totalmem } from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { getHeapStatistics } from 'node:v8';
import { humanBytes } from './dev-instance/format';

const GIB = 1024 ** 3;

/**
 * What one ESLint worker holds at its peak. Every worker builds its own typescript-eslint
 * programs for all the tsconfig projects it meets, so this is paid per worker, not shared.
 */
const BYTES_PER_WORKER = 4 * GIB;

/** Memory never handed to the lint: the larger of a fixed floor and a share of the machine. */
const MIN_RESERVE_BYTES = 4 * GIB;
const RESERVE_SHARE = 0.2;

/** Past four workers the run gets little faster while its memory keeps growing. */
const MAX_WORKERS = 4;

/**
 * Smallest heap ceiling ESLint and each of its workers get, in MiB. Node sizes its default heap
 * from a cgroup cap, and under a 10 GiB cap that default is too small for even one worker, which
 * then dies at the heap limit. Only a shrunk default is raised: a ceiling above Node's usual one
 * lets every worker hold more garbage, which costs more memory than it saves.
 */
const MIN_HEAP_MIB = 4096;

interface WorkerPlan {
  workers: number;
  available: number;
  reserve: number;
}

/**
 * Picks the worker count from the memory free when the lint starts.
 *
 * @remarks
 * `process.availableMemory()` follows the kernel's `MemAvailable` and any cgroup cap, so a run
 * inside a capped unit sizes itself to the cap. It is read once: memory claimed by something
 * started afterwards is not seen, which is why a reserve is kept free rather than spending all of
 * it. One worker is the floor even when it does not fit, since a lint cannot run on less.
 */
function planWorkers(): WorkerPlan {
  const total = Math.min(totalmem(), process.constrainedMemory() || Number.POSITIVE_INFINITY);
  const reserve = Math.max(MIN_RESERVE_BYTES, total * RESERVE_SHARE);
  const available = process.availableMemory();
  const byMemory = Math.floor((available - reserve) / BYTES_PER_WORKER);
  const byCpu = availableParallelism() - 1;
  const workers = Math.max(1, Math.min(MAX_WORKERS, byMemory, byCpu));
  return { workers, available, reserve };
}

function hasConcurrencyFlag(args: string[]): boolean {
  return args.some(arg => arg === '--concurrency' || arg.startsWith('--concurrency='));
}

/** Written to stderr so that `--format json` and other machine-read output stays parseable. */
function report(message: string): void {
  process.stderr.write(`${message}\n`);
}

function concurrencyArgs(args: string[]): string[] {
  if (hasConcurrencyFlag(args))
    return [];

  const { workers, available, reserve } = planWorkers();
  const memory = `${humanBytes(available)} available, ${humanBytes(reserve)} kept free`;
  if (available - reserve < BYTES_PER_WORKER)
    report(`eslint: linting single-threaded with only ${memory}; the machine may start swapping`);
  else
    report(`eslint: ${workers} ${workers === 1 ? 'worker' : 'workers'} (${memory})`);

  return [`--concurrency=${workers === 1 ? 'off' : workers}`];
}

/** ESLint's `exports` hide `bin/`, so the CLI is found beside its exported `package.json`. */
function eslintBin(): string {
  const manifest = createRequire(import.meta.url).resolve('eslint/package.json');
  return path.join(path.dirname(manifest), 'bin', 'eslint.js');
}

/** Keeps a heap size the caller already chose, and Node's default when it is not shrunk. */
function nodeOptions(): string {
  const current = process.env.NODE_OPTIONS ?? '';
  const defaultHeapMib = getHeapStatistics().heap_size_limit / 1024 ** 2;
  if (current.includes('--max-old-space-size') || defaultHeapMib >= MIN_HEAP_MIB)
    return current;
  return `${current} --max-old-space-size=${MIN_HEAP_MIB}`.trim();
}

const args = process.argv.slice(2);
const result = spawnSync(process.execPath, [eslintBin(), '.', ...concurrencyArgs(args), ...args], {
  env: { ...process.env, NODE_OPTIONS: nodeOptions() },
  stdio: 'inherit',
});
process.exit(result.status ?? 1);
