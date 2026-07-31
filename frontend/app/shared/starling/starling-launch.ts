import type { StarlingBackendOptions, StarlingInvocation } from './starling-args';
import type { StarlingRpc } from './starling-rpc';
import { type ChildProcess, spawn } from 'node:child_process';
import process from 'node:process';
import readline from 'node:readline';

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
  await rpc.request('start', { ...definedOptions(options), loglevel });
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
