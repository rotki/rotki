import type { StarlingRpc } from './starling-rpc';
import { type ChildProcess, spawn } from 'node:child_process';
import process from 'node:process';
import readline from 'node:readline';
import { SHUTDOWN_GRACE_SECS, type StarlingBackendOptions, type StarlingInvocation } from './starling-args';
import { StarlingMethod } from './starling-protocol';

/** How the supervisor went away: an exit code, or the signal that killed it. */
interface StarlingExit {
  code: number | null;
  signal: NodeJS.Signals | null;
}

/**
 * A spawned supervisor with the control channel attached. `exited` settles once
 * the child is gone, so callers can race a shutdown against it without
 * registering a second `exit` listener.
 */
export interface StarlingProcess {
  child: ChildProcess;
  exited: Promise<StarlingExit>;
}

export interface SpawnStarlingOptions {
  invocation: StarlingInvocation;
  /**
   * The control client to attach. Owned by the caller and reused across spawns,
   * so a restart that respawns keeps one client rather than orphaning pending
   * requests on a discarded one.
   */
  rpc: StarlingRpc;
  /** Called for each stderr line: starling's own logs plus inherited backend stderr. */
  onStderr: (line: string) => void;
}

/**
 * Spawn starling and wire its three stdio streams: stdin carries JSON-RPC
 * requests out, stdout carries responses and `event.*` notifications back, and
 * stderr carries log lines. Shared by the Electron handler and the dev launcher
 * so both drive the supervisor over the same channel — the only difference
 * between them is what they do with the lines.
 */
export function spawnStarling(options: SpawnStarlingOptions): StarlingProcess {
  const { invocation, rpc, onStderr } = options;

  const child = spawn(invocation.command, invocation.args, {
    cwd: invocation.cwd,
    // A complete env, not an overlay: spreading it over `process.env` would hand
    // a Windows child both `Path` and `PATH` and let it pick. See StarlingInvocation.
    env: invocation.env ?? process.env,
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  if (!child.stdout || !child.stderr || !child.stdin)
    throw new Error('starling child is missing its stdio pipes');

  rpc.attach(child.stdin);
  const out = readline.createInterface({ input: child.stdout });
  out.on('line', line => rpc.handleLine(line));

  const err = readline.createInterface({ input: child.stderr });
  err.on('line', onStderr);

  const exited = new Promise<StarlingExit>((resolve) => {
    child.on('exit', (code, signal) => {
      out.close();
      err.close();
      // Also unblocks an in-flight `start` if the child died before replying.
      rpc.rejectAll(new Error('starling exited'));
      rpc.detach();
      resolve({ code, signal });
    });
  });

  return { child, exited };
}

/**
 * Drive the first bring-up. starling boots idle in embedded mode and serves its
 * control channel immediately; this request is what starts the backend tree, and
 * it resolves only once the whole tree is ready. That makes it the readiness
 * gate — there is nothing to poll, and `event.ready` is informational.
 */
export async function requestStarlingStart(
  rpc: StarlingRpc,
  options: StarlingBackendOptions,
  loglevel: string,
): Promise<void> {
  await rpc.request(StarlingMethod.START, { ...definedOptions(options), loglevel });
}

/** The two lines this teardown has to say. Satisfied by LogService, consola and the dev logger alike. */
export interface StopStarlingLogger {
  debug: (message: string) => void;
  warn: (message: string) => void;
}

export interface StopStarlingOptions {
  /** The control client. Its `stop` is the ordered-teardown request. */
  rpc: StarlingRpc;
  child: ChildProcess;
  /** Settles once the child is gone — `StarlingProcess.exited`, or any promise that tracks it. */
  exited: Promise<unknown>;
  /**
   * How long `stop` may take to answer. starling only replies once the backend tree is down, which
   * it gives itself `SHUTDOWN_GRACE_SECS` to do, so anything shorter gives up on a shutdown that is
   * still going fine.
   */
  stopTimeoutMs?: number;
  /** Extra time the supervisor gets to exit itself once its own grace elapsed, before SIGKILL. */
  exitMarginMs?: number;
  logger?: StopStarlingLogger;
}

export interface StopStarlingResult {
  /** The child was already gone, so nothing was requested. */
  alreadyExited: boolean;
  /** `stop` answered within its timeout, rather than the timeout winning the race. */
  acknowledged: boolean;
  /** The supervisor had to be SIGKILLed because it outlasted both waits. */
  killed: boolean;
}

const SECOND = 1000;
const DEFAULT_EXIT_MARGIN_MS = 5_000;

/**
 * Local on purpose. `shared/utils.ts` has the same helper, but it is not in the tsconfig project
 * that compiles `shared/starling/` (TS6307), so importing it there does not typecheck — which is
 * why this timer was hand-written in each launcher to begin with.
 */
async function wait(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Ask starling to stop, give it its own grace, and only then kill it.
 *
 * ⚠️ The waits are not politeness. starling spawns core and colibri into their own process groups
 * precisely so it can reap them, which means **nothing else can**: killing the supervisor before its
 * escalation has run orphans both. That rule is the reason the supervisor exists, and it was
 * hand-written three times (electron, dev, e2e) with three different sets of mistakes before it
 * moved here.
 *
 * Callers keep their own re-entry guard. This function does not own one, because the flag also tells
 * each caller's `exit` handler whether the exit was expected, which is caller state — but it is safe
 * to call on an already-dead child, which it reports as `alreadyExited`.
 */
export async function stopStarling(options: StopStarlingOptions): Promise<StopStarlingResult> {
  const {
    rpc,
    child,
    exited,
    stopTimeoutMs = SHUTDOWN_GRACE_SECS * SECOND,
    exitMarginMs = DEFAULT_EXIT_MARGIN_MS,
    logger,
  } = options;

  if (child.exitCode !== null || child.signalCode !== null)
    return { acknowledged: false, alreadyExited: true, killed: false };

  logger?.debug('stopping starling');

  // A rejected `stop` is not a failure to handle: the child dying mid-request rejects every pending
  // one (see spawnStarling), and that is the outcome we were waiting for anyway.
  const acknowledged = await Promise.race([
    rpc.request(StarlingMethod.STOP).then(() => true).catch(() => false),
    wait(stopTimeoutMs).then(() => false),
  ]);

  // Second wait, on the child rather than the request: `stop` answering does not mean the process is
  // gone, and it timing out does not mean the shutdown failed.
  const exitedInTime = await Promise.race([
    exited.then(() => true),
    wait(exitMarginMs).then(() => false),
  ]);

  if (exitedInTime || child.exitCode !== null || child.signalCode !== null)
    return { acknowledged, alreadyExited: false, killed: false };

  logger?.warn('starling did not exit in time, killing it');
  child.kill('SIGKILL');
  return { acknowledged, alreadyExited: false, killed: true };
}

/**
 * The wire params for `start`/`restart`. Every BackendOptions field maps 1:1 to a
 * camelCase field starling accepts, and an absent field leaves that setting
 * unchanged, so only the set ones are sent.
 */
export function definedOptions(options: StarlingBackendOptions): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(options)) {
    if (value !== undefined)
      params[key] = value;
  }
  return params;
}
