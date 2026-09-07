import path from 'node:path';
import { buildCargoEnv } from '../cargo-env';
import {
  devBuiltBinary,
  devColibriLauncherArgs,
  devCoreLauncherArgs,
  packagedLauncherArgs,
  repoRoot,
  resolveStarlingBinary,
  STARLING_DIRECTORY,
} from './starling-launchers';

/**
 * Grace period starling gives the backend tree to exit before escalating to a
 * hard kill. Passed explicitly rather than relying on starling's own default so
 * this side knows the number: StarlingHandler.stop() must outwait it, or it
 * would SIGKILL starling mid-grace and orphan the very children starling was
 * about to reap.
 */
export const SHUTDOWN_GRACE_SECS = 10;

/**
 * The backend settings that reach starling on a `start`/`restart`, declared
 * structurally rather than imported from the app's `BackendOptions`. That type is
 * zod-derived and pulls the renderer's module graph in with it, which the dev and
 * e2e launchers — plain node, no bundler aliases — cannot resolve. The app's
 * `Partial<BackendOptions>` satisfies this shape, so callers pass theirs directly.
 */
export interface StarlingBackendOptions {
  loglevel?: string;
  dataDirectory?: string;
  logDirectory?: string;
  sleepSeconds?: number;
  logFromOtherModules?: boolean;
  maxSizeInMbAllLogs?: number;
  sqliteInstructions?: number;
  maxLogfilesNum?: number;
  mcpAutoStart?: boolean;
}

/**
 * How to launch the single `starling` supervisor child, fully resolved for the
 * current mode. `command`/`args` are passed straight to `spawn`; `cwd`/`env`
 * apply to that spawn (used in dev to run `cargo run` from the workspace).
 *
 * `env`, when set, is a COMPLETE environment that replaces `process.env` rather
 * than an overlay merged over it. Windows env keys are case-insensitive but Node
 * passes through whatever key you hand it, so spreading a `PATH` overlay onto a
 * `process.env` that has `Path` would send the child both - and which one wins is
 * undefined. See `buildCargoEnv`.
 */
export interface StarlingInvocation {
  command: string;
  args: string[];
  cwd?: string;
  env?: Record<string, string>;
}

export interface StarlingLaunchInput {
  isDev: boolean;
  /** Port allocated for the core REST API. */
  corePort: number;
  /** Port allocated for colibri. */
  colibriPort: number;
  /** Port allocated for the MCP streamable HTTP server. */
  mcpPort: number;
  /** Loopback port the in-process reverse proxy binds; the single renderer origin. */
  proxyPort: number;
  /**
   * Dev only: forward `/api/1/*` here instead of straight to `corePort`, putting
   * the premium dev-proxy between starling and core. The renderer keeps
   * addressing starling either way, so nothing downstream changes. Left undefined,
   * the flag is omitted entirely and a run is byte-identical to one from before the
   * option existed.
   */
  coreUpstreamPort?: number;
  /** Loopback host the backends bind (always 127.0.0.1 in embedded mode). */
  apiHost: string;
  /** Directory starling writes service logs to (owned by LogService). */
  logsDir: string;
  /** The persisted/UI backend options the renderer drives a (re)start with. */
  options: StarlingBackendOptions;
  /**
   * Origin the Vite dev server is serving the renderer from, added to the CORS
   * allowance in dev. Passed in rather than read from `import.meta.env` so this
   * module stays runnable outside a Vite bundle — the dev launcher imports it
   * straight from node and would see no `import.meta.env` at all.
   */
  devServerUrl?: string;
  /**
   * Absolute repo root, holding the cargo workspace and the python package.
   * Defaults to two levels above the cwd, which is right for Electron (it runs
   * from `frontend/app`) but not for the dev launcher, which runs from
   * `frontend` and passes its own.
   */
  repoRoot?: string;
  /**
   * Start core with its periodic task manager disabled. Set by the e2e harness,
   * which drives every query itself and would otherwise race background
   * refreshes. A launch fact, so it rides the CLI rather than BackendOptions.
   */
  disableTaskManager?: boolean;
}

/**
 * The CORS origins the backends must accept. The renderer is served from
 * `app://localhost` (packaged) or the Vite dev server (dev); `localhost:*` keeps
 * loopback tooling working. starling forwards this to both core and colibri.
 */
function corsOrigins(isDev: boolean, devServerUrl: string | undefined): string {
  if (!isDev)
    return 'app://*,http://localhost:*';
  if (!devServerUrl)
    return 'http://localhost:*';
  const trimmed = devServerUrl.endsWith('/') ? devServerUrl.slice(0, -1) : devServerUrl;
  return `${trimmed},http://localhost:*`;
}

/**
 * The mode-independent supervisor args: launch topology, addressing, dirs and
 * the shutdown grace. The mutable backend tunables (log level,
 * logfromothermodules, log-file limits, sqlite-instructions, sleep-secs) are NOT
 * passed here — the renderer sends them in the `start` control request (see
 * StarlingHandler), so they live in one place (BackendOptions) instead of being
 * mirrored on both CLI and RPC.
 */
function commonStarlingArgs(input: StarlingLaunchInput): string[] {
  const { options, corePort, colibriPort, mcpPort, proxyPort, apiHost, logsDir, isDev } = input;

  const args = [
    '--core-port',
    corePort.toString(),
    '--colibri-port',
    colibriPort.toString(),
    '--mcp-port',
    mcpPort.toString(),
    // The single origin the renderer talks to; core and colibri above are its upstreams.
    '--proxy-port',
    proxyPort.toString(),
    '--api-host',
    apiHost,
    '--api-cors',
    corsOrigins(isDev, input.devServerUrl),
    '--logs-dir',
    logsDir,
    '--shutdown-grace-secs',
    SHUTDOWN_GRACE_SECS.toString(),
  ];

  /*
   * Only forward a data dir when the user explicitly chose one. Otherwise starling computes the
   * platform default itself (production `data` versus `develop_data`), keyed to its own build via
   * the same version gate the backends use. Electron's `isDev`, a Vite build-time flag, does not
   * track the release tag, so deciding here would diverge for packaged nightlies. starling holds
   * the data-dir lock, so it owns the choice regardless.
   */
  if (options.dataDirectory) {
    args.push('--data-dir', options.dataDirectory);
  }

  // A launch fact, not a tunable: core cannot pick its task manager back up over the control channel.
  if (input.disableTaskManager) {
    args.push('--disable-task-manager');
  }

  if (input.coreUpstreamPort !== undefined) {
    args.push('--core-upstream-port', input.coreUpstreamPort.toString());
  }

  return args;
}

/**
 * Build the fully-resolved invocation for the single starling child: the
 * supervisor args plus the per-service launchers. Dev launches the binaries the
 * warm-up built (and the interpreter uv resolves), matching the packaged shape;
 * cargo is only a fallback for whichever build is missing.
 */
export function buildStarlingInvocation(input: StarlingLaunchInput): StarlingInvocation {
  if (!input.isDev) {
    return {
      command: resolveStarlingBinary(),
      args: [...commonStarlingArgs(input), ...packagedLauncherArgs()],
    };
  }

  const root = input.repoRoot ?? repoRoot();
  const colibri = devColibriLauncherArgs(root);
  const starlingArgs = [
    ...commonStarlingArgs(input),
    ...devCoreLauncherArgs(root),
    ...colibri.args,
  ];
  const built = devBuiltBinary(path.join(root, 'target'), STARLING_DIRECTORY);

  /*
   * The windows Strawberry Perl shim is needed by any cargo in the tree, and the two launchers
   * decide independently: starling may be prebuilt while colibri still falls back to `cargo run`
   * for vendored openssl, and that child inherits this env. Keying the shim off starling's own
   * branch would leave that case building openssl with the wrong perl.
   */
  const env = built && !colibri.usesCargo ? undefined : buildCargoEnv() ?? undefined;

  if (built)
    return { command: built, args: starlingArgs, cwd: root, env };

  return {
    command: 'cargo',
    args: ['run', '--locked', '-p', 'starling', '--', ...starlingArgs],
    cwd: root,
    env,
  };
}
