import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { buildCargoEnv } from '../cargo-env';
import { shouldUseUv } from '../uv';
import { BACKEND_DIRECTORY, findCoreBinary, resolveCoreBinary, resourcesDir } from './starling-paths';

const COLIBRI_DIRECTORY = 'colibri';
const STARLING_DIRECTORY = 'starling';

/**
 * Where a frozen core lands outside a packaged build, repo-root relative. Under
 * `target/` alongside the Rust binaries because that is where CI already drops
 * the artifacts it builds once and ships to the jobs that consume them, and it
 * is gitignored. Nothing writes here by default: a dev run without a freeze
 * falls through to the interpreter.
 */
const DEV_BACKEND_DIRECTORY = path.join('target', BACKEND_DIRECTORY);

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
 * Ask uv for the interpreter path rather than launching through `uv run`.
 *
 * starling must spawn the service itself, never a wrapper around it: it signals
 * the whole process group but `wait()`s only on its direct child, so a wrapper
 * that dies faster than the service reports "stopped" while the service is still
 * shutting down - starling then exits and the process-tree reap kills it
 * mid-flight. `uv run` does exactly that on windows: it installs no console-ctrl
 * handler, so CTRL_BREAK kills it instantly (0xC000013A) while python is still
 * closing its database, which leaves the sqlite WAL/SHM behind. Resolving the
 * interpreter up front keeps uv's environment handling and gives starling the
 * real process, matching the packaged launcher exactly.
 *
 * Returns undefined when uv can't answer, leaving the caller on its `python`
 * fallback.
 */
let resolvedUvPython: string | null | undefined;

function uvPythonPath(root: string): string | undefined {
  // Re-resolve if the cached interpreter has since gone (a venv recreated mid
  // session): the path is cached for the whole electron run, and a stale one
  // would otherwise fail every restart with ENOENT until the app is restarted.
  if (resolvedUvPython && !fs.existsSync(resolvedUvPython))
    resolvedUvPython = undefined;

  if (resolvedUvPython === undefined) {
    try {
      // `--no-sync`: the dev warm-up has already run `uv sync --locked`, so this
      // only has to report the interpreter. Skipping the resolve keeps it off the
      // seconds-long path — this runs synchronously on the electron main thread.
      const out = execSync('uv run --no-sync python -c "import sys; print(sys.executable)"', {
        cwd: root,
        encoding: 'utf-8',
        stdio: ['ignore', 'pipe', 'ignore'],
      });
      // Only the last line is ours: anything else uv chose to put on stdout would
      // otherwise be spliced into the path and spawned verbatim. `trimEnd` first
      // so the trailing newline does not make the last line an empty one.
      // (`findLast` would read better but this file is typechecked under the
      // renderer's DOM config, which pins lib to ES2022 to match vite's target.)
      const exe = out.trimEnd().split('\n').pop()?.trim();
      resolvedUvPython = exe && fs.existsSync(exe) ? exe : null;
    }
    catch {
      resolvedUvPython = null;
    }
  }
  return resolvedUvPython ?? undefined;
}

/** Absolute repo root, resolved from the electron app's cwd (`frontend/app`). */
function repoRoot(): string {
  return path.resolve(process.cwd(), '..', '..');
}

/** The bundled `starling` supervisor binary path for packaged builds. */
function resolveStarlingBinary(): string {
  const binary = process.platform === 'win32' ? 'starling.exe' : 'starling';
  return path.join(resourcesDir(), STARLING_DIRECTORY, binary);
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
    // Bind the reverse proxy on this loopback port; core and colibri (above) are
    // its upstream targets. The renderer talks to this single origin.
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

  // Only forward a data dir when the user explicitly chose one. Otherwise starling
  // computes the platform default itself (production `data` vs `develop_data`),
  // keyed to its own build via the same version gate the backends use. Electron's
  // `isDev` (a Vite build-time flag) does not track the release tag, so deciding
  // here would diverge for packaged nightlies — starling is the single source of
  // truth, and it holds the data-dir lock, so it must own the choice regardless.
  if (options.dataDirectory) {
    args.push('--data-dir', options.dataDirectory);
  }

  // A bare flag, and a launch fact rather than a tunable: core cannot be told to
  // pick its task manager back up over the control channel.
  if (input.disableTaskManager) {
    args.push('--disable-task-manager');
  }

  return args;
}

/** `[--flag=token, …]` for a launcher prefix (`--locked` etc. need the `=` form). */
function prefixFlags(flag: string, tokens: string[]): string[] {
  return tokens.map(token => `${flag}=${token}`);
}

/**
 * The dev core launcher: a profiling command, the interpreter uv resolves, or a
 * bare `python -m rotkehlchen` - whichever the dev environment dictates. Every
 * branch hands starling a real interpreter rather than a wrapper (see
 * `uvPythonPath`); with a venv active, `python` is already the venv's own.
 */
function devCoreLauncherArgs(root: string): string[] {
  // A frozen core, when the build job shipped one (see DEV_BACKEND_DIRECTORY).
  // Preferred over the interpreter for the same reason the packaged build uses
  // it: it exercises what actually ships, so a missing hidden import or data
  // file fails the e2e run rather than a release. No prefix - the binary is the
  // entrypoint, so `-m rotkehlchen` must not be passed - and its own directory
  // is the cwd, exactly as `packagedLauncherArgs` does.
  const frozen = findCoreBinary(path.join(root, DEV_BACKEND_DIRECTORY));
  if (frozen)
    return ['--core-binary', frozen.binary, '--core-cwd', frozen.dir];

  const profilingCmd = process.env.ROTKI_BACKEND_PROFILING_CMD;
  const profilingArgs = process.env.ROTKI_BACKEND_PROFILING_ARGS;
  // Interpreter args, so they precede `-m`: opt out of the GIL on a free-threaded
  // build. Same switch the web-mode launcher reads (`scripts/dev/services.ts`).
  const interpreterArgs = process.env.ROTKI_GIL === 'false' ? ['-X', 'gil=0'] : [];
  const moduleArgs = ['-m', 'rotkehlchen'];

  let binary: string;
  let prefix: string[];
  if (profilingCmd) {
    // The profiler runs python, so its own args come first and the interpreter
    // args attach to the `python` it launches.
    prefix = [
      ...(profilingArgs?.split(' ') ?? []).filter(Boolean),
      'python',
      ...interpreterArgs,
      ...moduleArgs,
    ];
    binary = profilingCmd;
  }
  else {
    binary = (shouldUseUv() ? uvPythonPath(root) : undefined) ?? 'python';
    prefix = [...interpreterArgs, ...moduleArgs];
  }

  return ['--core-binary', binary, ...prefixFlags('--core-prefix', prefix), '--core-cwd', root];
}

/**
 * A prebuilt binary for one of the Rust services, if there is one. Debug first,
 * since that is what the dev warm-up builds and what a developer expects their
 * last `cargo build` to have produced. Release is the fallback because CI builds
 * the services once with `--release` and ships only those binaries to the jobs
 * that consume them, where there is no cargo to fall back to.
 */
function devBuiltBinary(targetDir: string, name: string): string | undefined {
  const exe = process.platform === 'win32' ? `${name}.exe` : name;
  return ['debug', 'release']
    .map(profile => path.join(targetDir, profile, exe))
    .find(candidate => fs.existsSync(candidate));
}

/**
 * The dev colibri launcher: the binary the Rust warm-up built, falling back to
 * `cargo run --locked --` when it is missing (electron started without the
 * warm-up). The binary is preferred for the same reason core resolves its
 * interpreter - `cargo run` is a wrapper starling would `wait()` on instead of
 * colibri itself. The fallback keeps a warm-less launch working; colibri shuts
 * down in well under a millisecond, so losing the race there is unlikely.
 */
function devColibriLauncherArgs(root: string): { args: string[]; usesCargo: boolean } {
  const cwd = path.join(root, COLIBRI_DIRECTORY);
  const built = devBuiltBinary(path.join(root, 'target'), COLIBRI_DIRECTORY);
  if (built)
    return { args: ['--colibri-binary', built, '--colibri-cwd', cwd], usesCargo: false };

  return {
    args: [
      '--colibri-binary',
      'cargo',
      ...prefixFlags('--colibri-prefix', ['run', '--locked', '--']),
      '--colibri-cwd',
      cwd,
    ],
    usesCargo: true,
  };
}

/** Packaged launchers: direct binaries, each run from its own directory. */
function packagedLauncherArgs(): string[] {
  const core = resolveCoreBinary();
  const colibriDir = path.join(resourcesDir(), COLIBRI_DIRECTORY);
  const colibriBinary = process.platform === 'win32' ? 'colibri.exe' : 'colibri';
  return [
    '--core-binary',
    core.binary,
    '--core-cwd',
    core.dir,
    '--colibri-binary',
    path.join(colibriDir, colibriBinary),
    '--colibri-cwd',
    colibriDir,
  ];
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

  // The windows Strawberry Perl shim is needed by any cargo in the tree, and the
  // two launchers decide independently: starling may be prebuilt while colibri
  // still falls back to `cargo run` (vendored openssl), and that child inherits
  // this env. Keying the shim off starling's own branch would leave that case
  // building openssl with the wrong perl.
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
