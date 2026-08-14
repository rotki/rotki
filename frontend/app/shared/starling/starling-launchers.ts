/**
 * How each service is actually launched: which binary, from which directory,
 * behind which prefix. Split out of `starling-args.ts`, which owns the
 * supervisor's own arguments — this half answers "what runs", that half answers
 * "how it is configured".
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { shouldUseUv } from '../uv';
import { BACKEND_DIRECTORY, findCoreBinary, resolveCoreBinary, resourcesDir } from './starling-paths';

const COLIBRI_DIRECTORY = 'colibri';

export const STARLING_DIRECTORY = 'starling';

/**
 * Where a frozen core lands outside a packaged build, repo-root relative. Under
 * `target/` alongside the Rust binaries because that is where CI already drops
 * the artifacts it builds once and ships to the jobs that consume them, and it
 * is gitignored. Nothing writes here by default: a dev run without a freeze
 * falls through to the interpreter.
 */
const DEV_BACKEND_DIRECTORY = path.join('target', BACKEND_DIRECTORY);

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
export function repoRoot(): string {
  return path.resolve(process.cwd(), '..', '..');
}

/** The bundled `starling` supervisor binary path for packaged builds. */
export function resolveStarlingBinary(): string {
  const binary = process.platform === 'win32' ? 'starling.exe' : 'starling';
  return path.join(resourcesDir(), STARLING_DIRECTORY, binary);
}

/** `[--flag=token, …]` for a launcher prefix (`--locked` etc. need the `=` form). */
function prefixFlags(flag: string, tokens: string[]): string[] {
  return tokens.map(token => `${flag}=${token}`);
}

/** Which core a built invocation resolved to, for launchers that want to report it. */
export interface ResolvedCore {
  kind: 'frozen' | 'interpreter';
  binary?: string;
}

/**
 * Read back the core an invocation resolved to.
 *
 * `devCoreLauncherArgs` falls back to the interpreter silently when it finds no frozen build, and
 * nothing downstream records which one ran, so a wrong artifact path yields a passing run that
 * looks identical to a real one. The interpreter branch is the only one needing a prefix, since it
 * has to say `-m rotkehlchen`; the frozen binary is its own entrypoint. Prefix tokens arrive one
 * per flag as `--core-prefix=<token>`, so this matches the `=` form and not a bare flag.
 */
export function describeResolvedCore(args: string[]): ResolvedCore {
  const index = args.indexOf('--core-binary');
  return {
    binary: index === -1 ? undefined : args[index + 1],
    kind: args.some(arg => arg.startsWith('--core-prefix=')) ? 'interpreter' : 'frozen',
  };
}

/**
 * The dev core launcher: a profiling command, the interpreter uv resolves, or a
 * bare `python -m rotkehlchen` - whichever the dev environment dictates. Every
 * branch hands starling a real interpreter rather than a wrapper (see
 * `uvPythonPath`); with a venv active, `python` is already the venv's own.
 */
export function devCoreLauncherArgs(root: string): string[] {
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
export function devBuiltBinary(targetDir: string, name: string): string | undefined {
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
export function devColibriLauncherArgs(root: string): { args: string[]; usesCargo: boolean } {
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
export function packagedLauncherArgs(): string[] {
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
