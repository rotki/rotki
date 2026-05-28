import type { Buffer } from 'node:buffer';
import { type ChildProcess, spawn, spawnSync } from 'node:child_process';
import process from 'node:process';
import consola from 'consola';
import { errorCode, errorMessage } from '../dev-instance/format';

const isWindows = process.platform === 'win32';

interface OutputListener {
  out: (buffer: Buffer) => void;
  err: (buffer: Buffer) => void;
}

interface TrackedProcess {
  child: ChildProcess;
  name: string;
  listeners: OutputListener;
}

const SHUTDOWN_GRACE_MS = 5_000;

const logger = consola.withTag('dev:process-pool');
const tracked: TrackedProcess[] = [];

export interface SpawnOpts {
  cwd?: string;
  env?: Record<string, string | undefined>;
}

/**
 * Quotes a single argument so the shell (`shell: true` mode of spawn) treats
 * it as a single token. Without this, an arg like `--data-dir=/Users/jo/My
 * Project/data` gets re-split by /bin/sh on whitespace and the child sees
 * two broken args. Used for every arg we pass through process-pool because
 * we don't control whether the data-dir / log-path contains spaces.
 */
function shellQuoteArg(arg: string): string {
  if (arg === '')
    return '""';
  // Conservative allowlist of shell-safe chars — anything outside gets quoted.
  if (/^[\w%+,./:=@-]+$/.test(arg))
    return arg;
  if (process.platform === 'win32') {
    // cmd.exe: double-quote, escape inner double quotes by doubling.
    return `"${arg.replace(/"/g, '""')}"`;
  }
  // POSIX sh: single quotes preserve literally; escape any single-quote
  // inside by closing, inserting an escaped quote, and reopening.
  return `'${arg.replace(/'/g, '\'\\\'\'')}'`;
}

export function startProcess(cmd: string, tag: string, name: string, args: string[] = [], opts: SpawnOpts = {}): ChildProcess {
  const childLogger = consola.withTag(tag);
  const listeners: OutputListener = {
    out: (buffer: Buffer): void => {
      childLogger.log(buffer.toString().replace(/\n$/, ''));
    },
    err: (buffer: Buffer): void => {
      childLogger.log(buffer.toString().replace(/\n$/, ''));
    },
  };

  const env: NodeJS.ProcessEnv = {
    FORCE_COLOR: '1',
    ...process.env,
    NODE_ENV: 'development',
    ...(opts.env ?? {}),
  };

  // Node 24 deprecates passing `args` together with `shell: true` (DEP0190),
  // so we hand-build the full command string ourselves with each arg shell-
  // quoted. Functionally identical to spawn(cmd, args, {shell:true}) — the
  // shell concatenates them the same way — but the deprecation no longer fires.
  const fullCmd = args.length === 0
    ? cmd
    : `${cmd} ${args.map(shellQuoteArg).join(' ')}`;
  const child = spawn(fullCmd, {
    cwd: opts.cwd,
    shell: true,
    stdio: [process.stdin, 'pipe', 'pipe'],
    env,
    // POSIX: each child becomes its own process-group leader so a kill on
    // `-pid` reaches the whole tree (e.g. `cargo run` → colibri binary,
    // `pnpm run … serve` → vite). Without this, shell:true means SIGTERM
    // only kills the shell and the real worker leaks.
    //
    // Windows: detached:true with shell:true spawns a new console window
    // for every child, and POSIX process groups don't exist anyway — we
    // tree-kill via `taskkill /T /F` in `killGroup`. windowsHide keeps the
    // cmd.exe wrapper from flashing a console.
    detached: !isWindows,
    windowsHide: isWindows,
  });

  child.stdout?.on('data', listeners.out);
  child.stderr?.on('data', listeners.err);
  tracked.push({ child, name, listeners });
  return child;
}

function killGroup(pid: number, signal: NodeJS.Signals): void {
  if (isWindows) {
    // No POSIX process groups on Windows. `taskkill /T` walks the child
    // tree via the job/parent-pid table — this is the only reliable way
    // to reach cargo's spawned colibri.exe or pnpm's node workers.
    // `/F` is required because SIGINT/SIGTERM aren't deliverable to a
    // process that isn't sharing our console (cmd.exe shell wrappers).
    spawnSync('taskkill', ['/pid', String(pid), '/T', '/F'], { windowsHide: true });
    return;
  }
  try {
    process.kill(-pid, signal);
  }
  catch (error) {
    const code = errorCode(error);
    if (code === 'ESRCH')
      return; // already gone
    // EPERM or anything else: fall through to direct pid as a fallback.
    try {
      process.kill(pid, signal);
    }
    catch {
      // best-effort
    }
  }
}

function hasExited(child: ChildProcess): boolean {
  return child.killed || child.exitCode !== null;
}

function softKill(entry: TrackedProcess): boolean {
  const { child, name, listeners } = entry;
  if (hasExited(child))
    return false;
  const pid = child.pid;
  if (pid === undefined)
    return false;
  logger.info(`terminating process: ${name} (${pid})`);
  child.stdout?.off('data', listeners.out);
  child.stderr?.off('data', listeners.err);
  // SIGINT, not SIGTERM: detached:true puts each child in its own process
  // group, so the terminal's Ctrl+C never reaches them. Electron, vite and
  // cargo all install graceful SIGINT handlers (they expect Ctrl+C) but
  // electron's main process does not treat SIGTERM the same way and hangs
  // on shutdown. Match the Ctrl+C semantics they expect.
  killGroup(pid, 'SIGINT');
  return true;
}

async function waitForExit(survivors: TrackedProcess[], deadline: number): Promise<void> {
  while (Date.now() < deadline) {
    if (survivors.every(s => hasExited(s.child)))
      return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
}

function escalateSurvivors(survivors: TrackedProcess[]): void {
  for (const { child, name } of survivors) {
    if (hasExited(child))
      continue;
    const pid = child.pid;
    if (pid === undefined)
      continue;
    logger.warn(`escalating SIGKILL to ${name} (${pid}) after ${SHUTDOWN_GRACE_MS}ms grace`);
    killGroup(pid, 'SIGKILL');
  }
}

export async function terminateSubprocesses(): Promise<void> {
  const survivors: TrackedProcess[] = [];
  while (tracked.length > 0) {
    const entry = tracked.pop();
    if (entry && softKill(entry))
      survivors.push(entry);
  }
  if (survivors.length === 0)
    return;
  await waitForExit(survivors, Date.now() + SHUTDOWN_GRACE_MS);
  escalateSurvivors(survivors);
}

let shutdownRegistered = false;

export function registerShutdownHandlers(): void {
  if (shutdownRegistered)
    return;
  shutdownRegistered = true;
  const shutdown = (signal: NodeJS.Signals): void => {
    logger.info(`received ${signal}, terminating subprocesses`);
    terminateSubprocesses()
      .catch(error => logger.error(`shutdown error: ${errorMessage(error)}`))
      .finally(() => process.exit(0));
  };
  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGHUP', () => shutdown('SIGHUP'));
}
