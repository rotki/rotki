import path from 'node:path';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { describeResolvedCore } from './starling-args';

// The dev launchers probe the filesystem (is the warm-up build there?) and shell
// out to uv (which interpreter?). Both are mocked so these run identically on a
// CI box with no rust target dir and no uv installed.
const { existsSyncMock, statSyncMock, readdirSyncMock, execSyncMock, buildCargoEnvMock } = vi.hoisted(() => ({
  existsSyncMock: vi.fn(),
  statSyncMock: vi.fn(),
  readdirSyncMock: vi.fn(),
  execSyncMock: vi.fn(),
  buildCargoEnvMock: vi.fn(),
}));

// Stubbed so the cargo-env assertions hold on every platform: the real helper
// returns undefined off windows, which would make them windows-only.
const CARGO_ENV = { Path: 'C:\\Strawberry\\perl\\bin;C:\\Windows' };
vi.mock('@shared/cargo-env', () => ({
  buildCargoEnv: buildCargoEnvMock,
}));

// `statSync`/`readdirSync` are stubbed alongside `existsSync` because the core
// launcher probes for a frozen build, not just a file: with only `existsSync`
// mocked, a broad `true` sends the real `statSync` at a path that is not there.
vi.mock('node:fs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:fs')>();
  const stubs = { existsSync: existsSyncMock, statSync: statSyncMock, readdirSync: readdirSyncMock };
  return { ...actual, ...stubs, default: { ...actual, ...stubs } };
});

vi.mock('node:child_process', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:child_process')>();
  return { ...actual, default: { ...actual, execSync: execSyncMock }, execSync: execSyncMock };
});

const VENV_PYTHON = '/repo/.venv/bin/python';

const devInput = {
  isDev: true,
  corePort: 4242,
  colibriPort: 4343,
  mcpPort: 4445,
  proxyPort: 4141,
  apiHost: '127.0.0.1',
  logsDir: '/tmp/logs',
  options: {},
};

/**
 * `starling-args` caches uv detection and interpreter resolution in module
 * scope, so each case needs a fresh module graph to exercise its own stubs.
 */
async function buildDevInvocation(): Promise<import('./starling-args').StarlingInvocation> {
  vi.resetModules();
  const { buildStarlingInvocation } = await import('./starling-args');
  return buildStarlingInvocation(devInput);
}

function flagValue(args: string[], flag: string): string | undefined {
  const index = args.indexOf(flag);
  return index === -1 ? undefined : args[index + 1];
}

describe('buildStarlingInvocation (dev launchers)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.VIRTUAL_ENV;
    delete process.env.ROTKI_BACKEND_PROFILING_CMD;
    delete process.env.ROTKI_BACKEND_PROFILING_ARGS;
    delete process.env.ROTKI_GIL;
    buildCargoEnvMock.mockReturnValue(CARGO_ENV);
    statSyncMock.mockReturnValue({ isDirectory: () => true });
    // No frozen core unless a case says so, so the default stays the dev
    // interpreter every branch below asserts on.
    readdirSyncMock.mockReturnValue([]);
    execSyncMock.mockImplementation((cmd: string) => {
      if (cmd.includes('--version'))
        return '';
      return `${VENV_PYTHON}\n`;
    });
  });

  describe('when the warm-up builds are present', () => {
    beforeEach(() => {
      existsSyncMock.mockReturnValue(true);
    });

    it('should launch the built starling binary rather than cargo', async () => {
      const invocation = await buildDevInvocation();
      expect(invocation.command).not.toBe('cargo');
      expect(invocation.command).toMatch(/starling(\.exe)?$/);
    });

    it('should point colibri at the built binary rather than cargo', async () => {
      const { args } = await buildDevInvocation();
      expect(flagValue(args, '--colibri-binary')).toMatch(/colibri(\.exe)?$/);
      expect(args).not.toContain('--colibri-prefix=run');
    });

    it('should resolve both Rust binaries from the shared workspace target', async () => {
      const invocation = await buildDevInvocation();
      expect(invocation.command).toContain(path.join('target', 'debug'));
      expect(invocation.command).not.toContain(path.join('crates', 'target'));
      expect(flagValue(invocation.args, '--colibri-binary')).toContain(path.join('target', 'debug'));
      expect(flagValue(invocation.args, '--colibri-binary')).not.toContain(path.join('colibri', 'target'));
    });

    // The regression this guards: starling signals the whole process group but
    // wait()s only on its direct child. A wrapper that dies faster than the
    // service (uv takes CTRL_BREAK straight to the default terminator) reports
    // "stopped" while python is still closing its DB, and the tree reap then
    // kills it mid-shutdown - leaving the sqlite WAL/SHM behind.
    it('should resolve core to a real interpreter, never the uv wrapper', async () => {
      const { args } = await buildDevInvocation();
      expect(flagValue(args, '--core-binary')).toBe(VENV_PYTHON);
      expect(args).not.toContain('--core-prefix=run');
      expect(args).toContain('--core-prefix=-m');
      expect(args).toContain('--core-prefix=rotkehlchen');
    });

    it('should report the interpreter as the resolved core', async () => {
      const { args } = await buildDevInvocation();
      expect(describeResolvedCore(args)).toStrictEqual({ binary: VENV_PYTHON, kind: 'interpreter' });
    });
  });

  // The e2e run ships a frozen core the same way it ships the Rust binaries, so
  // the suite drives the binary that actually ships: a missing hidden import or
  // data file then fails the run rather than a release.
  describe('when a frozen core is present', () => {
    const FROZEN_CORE = 'rotki-core-1.43.0-linux';
    const frozenDir = path.join('target', 'backend', 'rotki-core');

    beforeEach(() => {
      existsSyncMock.mockReturnValue(true);
      readdirSyncMock.mockImplementation((probed: string) =>
        String(probed).includes(frozenDir) ? [FROZEN_CORE] : []);
    });

    it('should launch the frozen binary rather than an interpreter', async () => {
      const { args } = await buildDevInvocation();
      expect(flagValue(args, '--core-binary')).toContain(path.join(frozenDir, FROZEN_CORE));
      expect(flagValue(args, '--core-binary')).not.toBe(VENV_PYTHON);
    });

    // The binary is the entrypoint; passing `-m rotkehlchen` would have it
    // treat the module flags as its own CLI args and refuse to start.
    it('should not pass the module prefix', async () => {
      const { args } = await buildDevInvocation();
      expect(args).not.toContain('--core-prefix=-m');
      expect(args).not.toContain('--core-prefix=rotkehlchen');
    });

    // What the launcher logs, so a silent fall back to the interpreter is visible in a CI run
    // rather than looking exactly like a frozen one.
    it('should report the frozen binary as the resolved core', async () => {
      const { args } = await buildDevInvocation();
      const resolved = describeResolvedCore(args);
      expect(resolved.kind).toBe('frozen');
      expect(resolved.binary).toContain(path.join(frozenDir, FROZEN_CORE));
    });

    it('should run it from its own directory, as the packaged build does', async () => {
      const { args } = await buildDevInvocation();
      expect(flagValue(args, '--core-cwd')).toContain(frozenDir);
    });
  });

  // How CI runs: the build job compiles both services once with --release and
  // ships only those binaries, and the jobs that consume them have no rust
  // toolchain at all. Falling back to cargo there is not a slow path, it is a
  // dead one, so the release profile has to satisfy the same branch debug does.
  describe('when only the release profile is built', () => {
    beforeEach(() => {
      existsSyncMock.mockImplementation((p: string) => !String(p).includes(path.join('target', 'debug')));
    });

    it('should launch the release starling binary rather than cargo', async () => {
      const invocation = await buildDevInvocation();
      expect(invocation.command).not.toBe('cargo');
      expect(invocation.command).toContain(path.join('target', 'release'));
      expect(invocation.command).toMatch(/starling(\.exe)?$/);
    });

    it('should point colibri at the release binary rather than cargo', async () => {
      const { args } = await buildDevInvocation();
      expect(flagValue(args, '--colibri-binary')).toContain(path.join('target', 'release'));
      expect(args).not.toContain('--colibri-prefix=run');
    });

    it('should pass starling its own args, never cargo run args', async () => {
      // The CI failure this guards: the command was swapped to the release
      // binary while cargo's `run --locked -p starling --` args were kept, so
      // starling rejected its arguments and died before answering `start`.
      const { args } = await buildDevInvocation();
      expect(args).not.toContain('run');
      expect(args).not.toContain('--locked');
      expect(args[0]).toMatch(/^--/);
    });
  });

  it('should prefer the debug build when both profiles are present', async () => {
    existsSyncMock.mockReturnValue(true);
    const invocation = await buildDevInvocation();
    expect(invocation.command).toContain(path.join('target', 'debug'));
  });

  // The two launchers decide independently, so they can disagree: a prebuilt
  // starling still spawns colibri through cargo when only that build is missing.
  // The Strawberry Perl shim has to follow the cargo, not starling's own branch,
  // or that colibri builds vendored openssl with mingw perl and fails.
  it('should still pass the cargo env when only colibri falls back to cargo', async () => {
    existsSyncMock.mockImplementation((p: string) => !String(p).includes('colibri'));
    const invocation = await buildDevInvocation();
    expect(invocation.command).toMatch(/starling(\.exe)?$/);
    expect(flagValue(invocation.args, '--colibri-binary')).toBe('cargo');
    expect(invocation.env).toEqual(CARGO_ENV);
  });

  it('should not pass a cargo env when nothing needs cargo', async () => {
    existsSyncMock.mockReturnValue(true);
    const invocation = await buildDevInvocation();
    expect(invocation.env).toBeUndefined();
  });

  // StarlingHandler.stop() outwaits this same constant before it SIGKILLs, so
  // starling must be told the grace rather than left on its own default: the two
  // sides drifting means killing starling mid-teardown and orphaning a backend.
  it('should tell starling the shutdown grace it is held to', async () => {
    existsSyncMock.mockReturnValue(true);
    const { args } = await buildDevInvocation();
    const { SHUTDOWN_GRACE_SECS } = await import('./starling-args');
    expect(flagValue(args, '--shutdown-grace-secs')).toBe(SHUTDOWN_GRACE_SECS.toString());
  });

  it('should tell starling which MCP port Electron allocated', async () => {
    existsSyncMock.mockReturnValue(true);
    const { args } = await buildDevInvocation();
    expect(flagValue(args, '--mcp-port')).toBe(devInput.mcpPort.toString());
  });

  it('should tell starling which proxy port to bind', async () => {
    existsSyncMock.mockReturnValue(true);
    const { args } = await buildDevInvocation();
    expect(flagValue(args, '--proxy-port')).toBe(devInput.proxyPort.toString());
  });

  describe('when the warm-up builds are missing', () => {
    beforeEach(() => {
      existsSyncMock.mockReturnValue(false);
    });

    it('should fall back to compiling starling on the fly', async () => {
      const invocation = await buildDevInvocation();
      expect(invocation.command).toBe('cargo');
      expect(invocation.args.slice(0, 4)).toEqual(['run', '--locked', '-p', 'starling']);
      expect(invocation.cwd).toBeDefined();
      expect(invocation.cwd?.endsWith('crates')).toBe(false);
    });

    it('should fall back to running colibri through cargo', async () => {
      const { args } = await buildDevInvocation();
      expect(flagValue(args, '--colibri-binary')).toBe('cargo');
      expect(args).toContain('--colibri-prefix=run');
    });
  });

  it('should use the venv python directly when a virtualenv is active', async () => {
    existsSyncMock.mockReturnValue(true);
    process.env.VIRTUAL_ENV = '/repo/.venv';
    const { args } = await buildDevInvocation();
    expect(flagValue(args, '--core-binary')).toBe('python');
    // uv must not even be probed once a venv is active.
    expect(execSyncMock).not.toHaveBeenCalled();
  });

  it('should keep the profiling command as the core binary when set', async () => {
    existsSyncMock.mockReturnValue(true);
    process.env.ROTKI_BACKEND_PROFILING_CMD = 'py-spy';
    const { args } = await buildDevInvocation();
    expect(flagValue(args, '--core-binary')).toBe('py-spy');
  });

  // GIL opt-out, carried over from core-args when starling replaced it.
  describe('gIL', () => {
    beforeEach(() => {
      existsSyncMock.mockReturnValue(true);
      delete process.env.ROTKI_GIL;
    });

    it('should keep the GIL enabled by default', async () => {
      const { args } = await buildDevInvocation();
      expect(args).not.toContain('--core-prefix=gil=0');
    });

    // `-X gil=0` configures the interpreter, so it is only honoured ahead of
    // `-m`; after it, python passes it through to rotkehlchen as a module arg.
    it('should disable the GIL before the module args when ROTKI_GIL is false', async () => {
      process.env.ROTKI_GIL = 'false';
      const { args } = await buildDevInvocation();
      const prefix = args.filter(a => a.startsWith('--core-prefix='));
      expect(prefix).toEqual([
        '--core-prefix=-X',
        '--core-prefix=gil=0',
        '--core-prefix=-m',
        '--core-prefix=rotkehlchen',
      ]);
    });

    it('should hand the GIL switch to the python the profiler launches', async () => {
      process.env.ROTKI_GIL = 'false';
      process.env.ROTKI_BACKEND_PROFILING_CMD = 'py-spy';
      process.env.ROTKI_BACKEND_PROFILING_ARGS = 'record -o out.svg --';
      const { args } = await buildDevInvocation();
      expect(flagValue(args, '--core-binary')).toBe('py-spy');
      const prefix = args.filter(a => a.startsWith('--core-prefix=')).map(a => a.slice('--core-prefix='.length));
      expect(prefix).toEqual(['record', '-o', 'out.svg', '--', 'python', '-X', 'gil=0', '-m', 'rotkehlchen']);
    });
  });

  it('should fall back to python when uv cannot resolve an interpreter', async () => {
    existsSyncMock.mockReturnValue(true);
    execSyncMock.mockImplementation((cmd: string) => {
      if (cmd.includes('--version'))
        return '';
      throw new Error('uv exploded');
    });
    const { args } = await buildDevInvocation();
    expect(flagValue(args, '--core-binary')).toBe('python');
  });
});
