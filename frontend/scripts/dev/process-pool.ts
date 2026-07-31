import type { Buffer } from 'node:buffer';
import { type ChildProcess, spawn, spawnSync } from 'node:child_process';
import process from 'node:process';
import { errorCode, errorMessage } from '../dev-instance/format';
import { createDevLogger, formatDevLine } from './logger';

const isWindows = process.platform === 'win32';

interface OutputListener {
  out: (buffer: Buffer) => void;
  err: (buffer: Buffer) => void;
}

interface TrackedProcess {
  child: ChildProcess;
  name: string;
  listeners: OutputListener;
  windowed: boolean;
}

const SHUTDOWN_GRACE_MS = 5_000;

const logger = createDevLogger('dev:process-pool');
const tracked: TrackedProcess[] = [];

export interface SpawnOpts {
  cwd?: string;
  env?: Record<string, string | undefined>;
  /**
   * Windows: this child owns a window, so it can be asked to close politely and
   * given the grace period to do it. Windowless console children (every `cmd.exe`
   * wrapper we spawn) reject a polite close outright, so asking only burns the
   * whole grace before the forced kill that was always going to happen. Ignored
   * on POSIX, where the signal itself is the graceful request.
   */
  windowed?: boolean;
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
  // Format each child line as `<label> <time> <line>` on the LEFT and write it
  // straight through. consola's tagged reporter right-aligned the tag+timestamp
  // to the terminal width, which misfired on multi-line chunks and on any line
  // wider than the terminal (the badge wrapped in front of the next line). A plain
  // left format is stable regardless of line length. Split per line so a chunk
  // carrying several lines is formatted line-by-line.
  const emit = (buffer: Buffer): void => {
    for (const line of buffer.toString().split(/\r?\n/)) {
      if (line.length > 0)
        process.stdout.write(`${formatDevLine(tag, line)}\n`);
    }
  };
  const listeners: OutputListener = { out: emit, err: emit };

  const env: NodeJS.ProcessEnv = {
    FORCE_COLOR: '1',
    // The forwarder prepends its own `<label> <time>` to every child line, so tell
    // child tools (Vite) to drop their own timestamp and avoid a doubled clock.
    ROTKI_DEV_FORWARDED: '1',
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
  tracked.push({ child, name, listeners, windowed: opts.windowed ?? false });
  return child;
}

function killGroup(pid: number, signal: NodeJS.Signals, windowed = false): void {
  if (isWindows) {
    // No POSIX process groups on Windows. `taskkill /T` walks the child
    // tree via the job/parent-pid table — this is the only reliable way
    // to reach cargo's spawned colibri.exe or pnpm's node workers.
    //
    // `/F` is an unconditional TerminateProcess. Forcing a windowed child during
    // the graceful phase kills electron mid-quit, before it can run its ordered
    // backend teardown, so those get a polite close (WM_CLOSE) instead and their
    // exit unwinds the serve/pnpm/cmd chain behind them.
    //
    // Everything else we spawn is a windowless console process, which rejects a
    // polite close outright. Asking anyway would just burn the whole grace period
    // before the forced kill that was always going to happen.
    const force = windowed && signal !== 'SIGKILL' ? [] : ['/F'];
    spawnSync('taskkill', ['/pid', String(pid), '/T', ...force], { windowsHide: true });
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
  const { child, name, listeners, windowed } = entry;
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
  killGroup(pid, 'SIGINT', windowed);
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

type ShutdownHook = () => Promise<void>;

const hooks: ShutdownHook[] = [];

/**
 * Register work that must run before the tracked children are signalled.
 * `startProcess` inherits stdin, so a child driven over a stdio control channel
 * (starling) cannot live in the pool — it spawns itself and hooks in here to get
 * its graceful stop ahead of the generic kill.
 */
export function registerShutdownHook(hook: ShutdownHook): void {
  hooks.push(hook);
}

async function runShutdownHooks(): Promise<void> {
  while (hooks.length > 0) {
    const hook = hooks.pop();
    if (!hook)
      continue;
    try {
      await hook();
    }
    catch (error) {
      logger.error(`shutdown hook failed: ${errorMessage(error)}`);
    }
  }
}

export async function terminateSubprocesses(): Promise<void> {
  await runShutdownHooks();
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
