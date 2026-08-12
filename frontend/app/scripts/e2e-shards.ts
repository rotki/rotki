import type { Buffer } from 'node:buffer';
import { type ChildProcess, spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import process from 'node:process';
import { cac } from 'cac';
import consola from 'consola';

/**
 * Runs the e2e suite as several shards in parallel on one machine.
 *
 * The backend is single-user, so a single Playwright run is pinned to one worker and
 * takes around twenty minutes. This starts N complete stacks instead - each its own
 * starling supervisor (core, colibri, the proxy), rpc mock and preview server - and
 * gives each one a shard of the suite.
 *
 * Shards are numbered from 1 and take the port block at that number's offset, so the
 * base block stays free and a plain `pnpm test:e2e` can run alongside a sharded one.
 * `playwright.config.ts` derives every port, data directory and report path from
 * `E2E_SHARD` plus `E2E_PORT_OFFSET`, both set here.
 *
 * Every shard serves the same bundle. It can, because the bundle names no port: it is
 * built with an empty `VITE_BACKEND_URL` so all calls go same-origin, and each preview
 * server proxies them to its own shard's starling (see `preview.proxy` in
 * vite.config.ts). One build, N stacks.
 */

/** Matches PORT_BLOCK_STRIDE and the base ports in playwright.config.ts. */
const PORT_STRIDE = 10;
const BASE_PORTS = [30301, 30302, 30303, 30304, 30305, 30306];
const PORT_LABELS = ['frontend', 'core', 'colibri', 'rpc-mock', 'proxy', 'mcp'];

/** playwright.config.ts probes ten blocks, and shard 1 takes the second of them. */
const MAX_SHARDS = 9;

/**
 * Rough resident-set cost of one shard: preview server, core, colibri, starling,
 * Playwright and its chromium. Used only to warn before a run; the measured peaks
 * printed at the end are the number to trust.
 */
const ESTIMATED_SHARD_MEMORY_MB = 1500;

/** How often the memory sampler reads the process table. */
const SAMPLE_INTERVAL_MS = 10_000;

/** Lines worth surfacing from a shard's output when not running verbose. */
const INTERESTING_OUTPUT = /^\s*(?:\d+ (?:passed|failed|flaky|skipped)|Running \d+ test|✘|Error:|\d+\) )/;

const appDir = path.resolve(import.meta.dirname, '..');
const e2eDir = path.join(appDir, '.e2e');
const templateDir = path.join(e2eDir, 'template');
const blobDir = path.join(e2eDir, 'blob-report');
const reportDir = path.join(appDir, 'playwright-report');
// Also read by `e2e-reset-global-db.ts`, which gives the unsharded run the same clean start.
const packagedGlobalDb = path.join(appDir, '..', '..', 'rotkehlchen', 'data', 'global.db');

interface RunOptions {
  shards: number;
  resetTemplate: boolean;
  skipBuild: boolean;
  verbose: boolean;
  passthrough: string[];
}

function shardDir(shard: number): string {
  return path.join(e2eDir, `shard-${shard}`);
}

function portOffsetFor(shard: number): number {
  return shard * PORT_STRIDE;
}

/**
 * Checks whether something is already listening on a port. Connects over both loopback
 * families: vite binds ::1 while core binds 127.0.0.1, so checking one family misses
 * half the stack.
 */
async function isPortFree(port: number): Promise<boolean> {
  const probes = ['127.0.0.1', '::1'].map(async host => new Promise<boolean>((resolve) => {
    const socket = net.connect({ host, port });
    const done = (inUse: boolean): void => {
      socket.destroy();
      resolve(inUse);
    };
    socket.setTimeout(500);
    socket.on('connect', () => done(true));
    socket.on('timeout', () => done(false));
    socket.on('error', () => done(false));
  }));

  const results = await Promise.all(probes);
  return !results.includes(true);
}

/**
 * Best-effort description of whoever holds a port, so a collision names the culprit
 * instead of failing minutes later as an opaque webServer timeout.
 */
function describePortHolder(port: number): string {
  try {
    const listeners = spawnSync('ss', ['-ltnp'], { encoding: 'utf-8' });
    const line = listeners.stdout?.split('\n').find(entry => new RegExp(`[.:]${port}\\s`).test(entry));
    const pid = line?.match(/pid=(\d+)/)?.[1];
    if (!pid) {
      return line?.trim() ?? 'unknown process';
    }
    const cmdline = fs.readFileSync(`/proc/${pid}/cmdline`, 'utf-8').replaceAll('\0', ' ').trim();
    return `pid ${pid}: ${cmdline}`;
  }
  catch {
    return 'unknown process';
  }
}

async function preflightPorts(shards: number): Promise<void> {
  const conflicts: string[] = [];

  for (let shard = 1; shard <= shards; shard++) {
    for (const [index, basePort] of BASE_PORTS.entries()) {
      const port = basePort + portOffsetFor(shard);
      if (!await isPortFree(port)) {
        conflicts.push(`  shard ${shard} ${PORT_LABELS[index]} port ${port}: ${describePortHolder(port)}`);
      }
    }
  }

  if (conflicts.length > 0) {
    consola.error(`Cannot start, ports are already in use:\n${conflicts.join('\n')}`);
    consola.info('Stop the processes above, or run with fewer shards (-n).');
    process.exit(1);
  }
}

/**
 * Reads MemAvailable, the kernel's own estimate of what can be handed out without
 * swapping. `os.freemem()` is the wrong number on linux: it excludes reclaimable page
 * cache and so understates what is available, often by tens of gigabytes.
 */
function availableMemoryMb(): number | undefined {
  try {
    const meminfo = fs.readFileSync('/proc/meminfo', 'utf-8');
    const kb = meminfo.match(/^MemAvailable:\s+(\d+) kB$/m)?.[1];
    return kb ? Math.round(Number(kb) / 1024) : undefined;
  }
  catch {
    return undefined;
  }
}

/** Warns, never blocks: the estimate is coarse and the machine is the user's to fill. */
function warnOnMemory(shards: number): void {
  const available = availableMemoryMb();
  if (available === undefined) {
    return;
  }

  const needed = shards * ESTIMATED_SHARD_MEMORY_MB;
  const format = (mb: number): string => `${(mb / 1024).toFixed(1)} GB`;

  if (needed > available) {
    consola.warn(
      `${shards} shards need roughly ${format(needed)} but only ${format(available)} is available. `
      + 'Expect swapping or an out-of-memory kill; run with fewer shards (-n) if that matters.',
    );
  }
  else {
    consola.info(`${shards} shards need roughly ${format(needed)}, ${format(available)} available`);
  }
}

/** Uses cp so copy-on-write is used where the filesystem supports it. */
function copyTree(source: string, target: string): void {
  const result = spawnSync('cp', ['-a', '--reflink=auto', source, target], { stdio: 'inherit' });
  if (result.status !== 0) {
    throw new Error(`Failed to copy ${source} to ${target}`);
  }
}

/**
 * Builds the template data directory every shard starts from.
 *
 * The template is the packaged global database, which is what the backend copies into a
 * fresh data directory itself (globaldb/handler.py). Seeding it here means no shard pays
 * for that bootstrap, and every run starts from a pristine database rather than one
 * carrying state from previous runs - the manual price rows that accumulate in a reused
 * data directory break the price-manager specs.
 *
 * The icon cache is carried over from a previous run when there is one. It is a pure
 * cache, so a missing one only costs a little time.
 */
function prepareTemplate(resetTemplate: boolean): void {
  if (resetTemplate && fs.existsSync(templateDir)) {
    fs.rmSync(templateDir, { recursive: true, force: true });
  }

  const templateDb = path.join(templateDir, 'global', 'global.db');
  if (!fs.existsSync(packagedGlobalDb)) {
    throw new Error(`Packaged global database not found at ${packagedGlobalDb}`);
  }

  // Rebuild when the packaged database has moved on, e.g. after a data submodule bump.
  const stale = fs.existsSync(templateDb)
    && fs.statSync(templateDb).mtimeMs < fs.statSync(packagedGlobalDb).mtimeMs;

  if (stale || !fs.existsSync(templateDb)) {
    consola.info('Seeding the data template from the packaged global database');
    fs.rmSync(path.join(templateDir, 'global'), { recursive: true, force: true });
    fs.mkdirSync(path.join(templateDir, 'global'), { recursive: true });
    copyTree(packagedGlobalDb, templateDb);
  }

  const cachedIcons = path.join(e2eDir, 'data', 'images');
  const templateIcons = path.join(templateDir, 'images');
  if (fs.existsSync(cachedIcons) && !fs.existsSync(templateIcons)) {
    copyTree(cachedIcons, templateIcons);
  }
}

function resetShardData(shard: number): void {
  const dataDir = path.join(shardDir(shard), 'data');
  fs.rmSync(dataDir, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(dataDir), { recursive: true });
  copyTree(templateDir, dataDir);
}

/**
 * Builds the one bundle every shard shares.
 *
 * Clearing `VITE_BACKEND_URL` rather than omitting it is what makes the bundle portable:
 * `.env` points the backend at port 4242 and the build injects it, so an omitted value
 * would bake that in and the app would boot against a port nothing is listening on.
 */
function buildFrontend(): void {
  consola.info('Building the frontend bundle shared by every shard');
  const started = Date.now();

  const result = spawnSync('npx', ['tsx', 'scripts/build.ts', '--mode', 'e2e', '--renderer-only'], {
    cwd: appDir,
    env: { ...process.env, VITE_BACKEND_URL: '' },
    stdio: ['ignore', 'ignore', 'inherit'],
  });

  if (result.status !== 0) {
    throw new Error('Frontend build failed');
  }

  consola.success(`Frontend built in ${((Date.now() - started) / 1000).toFixed(0)}s`);
}

/** Every shard process group started by this run, so they can all be cleaned up. */
const shardGroups = new Set<number>();

/**
 * Kills a shard and everything it started. Playwright's webServer children are in the
 * shard's process group, so killing the group takes starling, the rpc mock and the
 * preview server with it. Without this an interrupted run leaves a full stack per shard
 * resident indefinitely.
 */
function killGroup(pgid: number, signal: NodeJS.Signals): void {
  try {
    process.kill(-pgid, signal);
  }
  catch {
    // Already gone.
  }
}

function killAllShards(signal: NodeJS.Signals): void {
  for (const pgid of shardGroups) {
    killGroup(pgid, signal);
  }
}

function installCleanupHandlers(): void {
  for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP'] as const) {
    process.on(signal, () => {
      consola.warn(`Received ${signal}, stopping ${shardGroups.size} shard(s)`);
      killAllShards('SIGTERM');
      // Give the stacks a moment to shut down cleanly, then insist.
      setTimeout(() => {
        killAllShards('SIGKILL');
        process.exit(130);
      }, 5000).unref();
    });
  }

  process.on('exit', () => killAllShards('SIGKILL'));
}

/**
 * Sums resident memory per process group, so each shard's whole stack is measured as one
 * number. Returns megabytes keyed by process group id.
 */
function sampleGroupMemoryMb(): Map<number, number> {
  const totals = new Map<number, number>();
  const result = spawnSync('ps', ['-eo', 'pgid=,rss='], { encoding: 'utf-8' });

  for (const line of result.stdout?.split('\n') ?? []) {
    const [pgid, rss] = line.trim().split(/\s+/).map(Number);
    if (!shardGroups.has(pgid) || Number.isNaN(rss)) {
      continue;
    }
    totals.set(pgid, (totals.get(pgid) ?? 0) + rss / 1024);
  }

  return totals;
}

/**
 * Streams a shard's output to its own log file and forwards only the lines worth reading
 * to the terminal. Several shards each emitting a full reporter for twenty minutes is
 * far more than anything capturing this run wants to hold.
 */
function pipeOutput(child: ChildProcess, shard: number, verbose: boolean): void {
  const logPath = path.join(shardDir(shard), 'logs', 'shard.log');
  fs.mkdirSync(path.dirname(logPath), { recursive: true });
  const log = fs.createWriteStream(logPath);
  const prefix = `[${shard}] `;
  let pending = '';

  for (const stream of [child.stdout, child.stderr]) {
    stream?.on('data', (chunk: Buffer) => {
      const text = chunk.toString();
      log.write(text);

      pending += text;
      const lines = pending.split('\n');
      pending = lines.pop() ?? '';

      const shown = verbose ? lines : lines.filter(line => INTERESTING_OUTPUT.test(line));
      if (shown.length > 0) {
        process.stdout.write(`${shown.map(line => `${prefix}${line}`).join('\n')}\n`);
      }
    });
  }

  child.on('exit', () => log.end());
}

interface ShardResult {
  code: number;
  peakMemoryMb: number;
}

async function runShard(
  shard: number,
  shards: number,
  passthrough: string[],
  verbose: boolean,
): Promise<ShardResult> {
  const args = ['playwright', 'test', `--shard=${shard}/${shards}`, ...passthrough];
  const child = spawn('npx', args, {
    cwd: appDir,
    // Its own process group, so cleanup and memory accounting can address the whole
    // stack rather than just the playwright process.
    detached: true,
    env: {
      ...process.env,
      E2E_SHARD: String(shard),
      E2E_PORT_OFFSET: String(portOffsetFor(shard)),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  const pgid = child.pid;
  if (pgid !== undefined) {
    shardGroups.add(pgid);
  }

  pipeOutput(child, shard, verbose);

  const logPath = path.join(shardDir(shard), 'logs', 'shard.log');
  consola.info(`Shard ${shard}/${shards} started, full output in ${path.relative(appDir, logPath)}`);

  return new Promise<ShardResult>((resolve) => {
    let peakMemoryMb = 0;
    const sampler = setInterval(() => {
      if (pgid === undefined) {
        return;
      }
      peakMemoryMb = Math.max(peakMemoryMb, sampleGroupMemoryMb().get(pgid) ?? 0);
    }, SAMPLE_INTERVAL_MS);
    sampler.unref();

    child.on('exit', (code) => {
      clearInterval(sampler);
      if (pgid !== undefined) {
        // Playwright stops its own webServers, but a crashed or killed shard may not
        // have; make sure nothing outlives the run.
        killGroup(pgid, 'SIGKILL');
        shardGroups.delete(pgid);
      }
      consola.info(`Shard ${shard}/${shards} finished with code ${code ?? 0}, peak ${peakMemoryMb.toFixed(0)} MB`);
      resolve({ code: code ?? 1, peakMemoryMb });
    });
  });
}

function mergeReports(): void {
  if (!fs.existsSync(blobDir) || fs.readdirSync(blobDir).length === 0) {
    consola.warn('No blob reports to merge');
    return;
  }

  const result = spawnSync('npx', ['playwright', 'merge-reports', '--reporter', 'html', blobDir], {
    cwd: appDir,
    env: { ...process.env, PLAYWRIGHT_HTML_OPEN: 'never', PLAYWRIGHT_HTML_OUTPUT_DIR: reportDir },
    stdio: 'inherit',
  });

  if (result.status === 0) {
    consola.success(`Merged report written to ${path.relative(appDir, reportDir)}`);
  }
  else {
    consola.error('Failed to merge shard reports');
  }
}

function hasBundle(): boolean {
  return fs.existsSync(path.join(appDir, 'dist', 'index.html'));
}

async function run(options: RunOptions): Promise<void> {
  const { shards, resetTemplate, skipBuild, verbose, passthrough } = options;

  if (shards < 1 || shards > MAX_SHARDS) {
    consola.error(`The number of shards must be between 1 and ${MAX_SHARDS}`);
    process.exit(1);
  }

  if (shards > 1 && process.env.MOCK_RPC_MODE === 'record') {
    consola.error('Cassette recording writes shared files and cannot be sharded. Record with a single shard.');
    process.exit(1);
  }

  warnOnMemory(shards);
  await preflightPorts(shards);
  prepareTemplate(resetTemplate);

  if (skipBuild) {
    if (!hasBundle()) {
      consola.error('--skip-build was given but there is no bundle in dist/. Run without it once.');
      process.exit(1);
    }
    consola.info('Reusing the existing frontend bundle');
  }
  else {
    buildFrontend();
  }

  fs.rmSync(blobDir, { recursive: true, force: true });

  for (let shard = 1; shard <= shards; shard++) {
    resetShardData(shard);
  }

  installCleanupHandlers();

  consola.box(`Running the e2e suite across ${shards} shards`);
  const started = Date.now();

  const results = await Promise.all(
    Array.from({ length: shards }, async (_, index) => runShard(index + 1, shards, passthrough, verbose)),
  );

  const minutes = ((Date.now() - started) / 60_000).toFixed(1);
  mergeReports();

  const peak = Math.max(...results.map(result => result.peakMemoryMb));
  const total = results.reduce((sum, result) => sum + result.peakMemoryMb, 0);
  consola.info(`Peak memory: ${peak.toFixed(0)} MB for the heaviest shard, ${total.toFixed(0)} MB across all shards`);

  const failed = results.filter(result => result.code !== 0).length;
  if (failed > 0) {
    consola.error(`${failed} of ${shards} shards failed after ${minutes} minutes`);
    process.exit(1);
  }

  consola.success(`All ${shards} shards passed in ${minutes} minutes`);
}

/**
 * Splits our own flags from what is forwarded to Playwright.
 *
 * Spec paths are plain positional arguments, so the common case needs no separator:
 * `pnpm run test:e2e:shards -n 2 tests/e2e/specs/app/tag-manager.spec.ts`. A `--` is
 * still honoured for raw Playwright flags this script knows nothing about, e.g.
 * `... -n 2 -- --grep @slow`.
 *
 * pnpm 11 forwards arguments verbatim, so a `--` typed out of npm habit arrives as a
 * literal leading token rather than being eaten by the package manager. Dropping it
 * here keeps both spellings working.
 */
function splitArguments(): { own: string[]; forwarded: string[] } {
  const argv = process.argv.slice(2);
  if (argv[0] === '--') {
    argv.shift();
  }

  const separator = argv.indexOf('--');
  return separator === -1
    ? { own: argv, forwarded: [] }
    : { own: argv.slice(0, separator), forwarded: argv.slice(separator + 1) };
}

const { own, forwarded } = splitArguments();
const cli = cac();

cli.command('[...specs]', 'Run the e2e suite as parallel shards')
  .option('-n, --shards <count>', 'Number of parallel shards', { default: 4 })
  .option('--reset-template', 'Rebuild the data template before running', { default: false })
  .option('--skip-build', 'Reuse the frontend bundle from a previous run', { default: false })
  .option('--verbose', 'Stream every shard\'s full output instead of a summary', { default: false })
  .action(async (specs: string[], options) => {
    await run({
      passthrough: [...specs, ...forwarded],
      resetTemplate: Boolean(options.resetTemplate),
      shards: Number(options.shards),
      skipBuild: Boolean(options.skipBuild),
      verbose: Boolean(options.verbose),
    });
  });

cli.help();
cli.parse([process.argv[0], process.argv[1], ...own]);
