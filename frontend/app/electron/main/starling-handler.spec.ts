import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import { EventEmitter } from 'node:events';
import { PassThrough, Writable } from 'node:stream';
import { BackendCode, StarlingServiceStatus } from '@shared/ipc';
import { LogLevel } from '@shared/log-level';
import { BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';
import { StarlingEvent, StarlingMethod, StarlingService } from '@shared/starling/starling-protocol';
import { QUARANTINED_COLIBRI, QUARANTINED_STARLING } from '@test/fixtures/unusable-binary';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { StarlingHandler } from './starling-handler';

// Mutable os identity for the version gates; the rest of the builtin stays real for cargo-env.
const osState = { platform: 'linux', release: '5.0.0' };
vi.mock('node:os', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:os')>();
  const identity = {
    platform: (): string => osState.platform,
    release: (): string => osState.release,
  };
  return { ...actual, default: { ...actual, ...identity }, ...identity };
});

// `spawn` hands back whatever fake child the test installs; the rest of the builtin stays real.
const { buildStarlingInvocationMock, selectPortMock, spawnMock } = vi.hoisted(() => ({
  buildStarlingInvocationMock: vi.fn(),
  selectPortMock: vi.fn(),
  spawnMock: vi.fn(),
}));
vi.mock('node:child_process', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:child_process')>();
  return { ...actual, default: { ...actual, spawn: spawnMock }, spawn: spawnMock };
});

// Only the builder is stubbed: SHUTDOWN_GRACE_SECS feeds the stop timeouts and would go NaN.
vi.mock('@shared/starling/starling-args', async importOriginal => ({
  ...await importOriginal<typeof import('@shared/starling/starling-args')>(),
  buildStarlingInvocation: buildStarlingInvocationMock,
}));

vi.mock('@shared/port-utils', () => ({
  selectPort: selectPortMock,
}));

// The real check stats the packaged install, which is not there under test; healthy by default.
const { findUnusableBinaryMock, refusedStarlingMock } = vi.hoisted(() => ({
  findUnusableBinaryMock: vi.fn<() => UnusableBinary | undefined>(),
  refusedStarlingMock: vi.fn<(error: unknown) => UnusableBinary | undefined>(),
}));
vi.mock('@shared/starling/binary-health', () => ({
  findUnusableBinary: findUnusableBinaryMock,
  refusedStarling: refusedStarlingMock,
}));

interface FakeChild extends EventEmitter {
  stdin: Writable;
  stdout: PassThrough;
  stderr: PassThrough;
  kill: ReturnType<typeof vi.fn>;
}

type RequestHandler = (
  message: { id?: number; method?: string; params?: Record<string, unknown> },
  stdout: PassThrough,
) => void;

/** A starling stand-in: stdin parses JSON-RPC, the responder answers on stdout. */
function makeFakeChild(onRequest: RequestHandler): FakeChild {
  const stdout = new PassThrough();
  const stderr = new PassThrough();
  const stdin = new Writable({
    write(chunk, _encoding, callback): void {
      const line = chunk.toString().trim();
      if (line)
        onRequest(JSON.parse(line), stdout);
      callback();
    },
  });
  const child: FakeChild = Object.assign(new EventEmitter(), { stdin, stdout, stderr, kill: vi.fn() });
  return child;
}

function writeMessage(stdout: PassThrough, message: Record<string, unknown>): void {
  stdout.write(`${JSON.stringify({ jsonrpc: '2.0', ...message })}\n`);
}

/** Replies to any request with a null result (control RPCs the tests don't drive). */
const nullResponder: RequestHandler = (message, stdout): void => {
  writeMessage(stdout, { id: message.id, result: null });
};

/** Push the controller's initial `ready` event, as starling does once the tree is up. */
function emitReady(child: FakeChild): void {
  writeMessage(child.stdout, {
    method: StarlingEvent.READY,
    params: { services: [StarlingService.CORE, StarlingService.COLIBRI] },
  });
}

/**
 * Accepts overrides so a test that asserts on a log line can hold the spy itself rather than
 * reaching for `logger.info`, which would be an unbound method reference.
 */
function makeLogger(overrides: Partial<LogService> = {}): LogService {
  return createMock<LogService>({
    getLogLevel: vi.fn(() => LogLevel.INFO),
    get coreProcessLogPath(): string {
      return '/tmp/logs/rotkehlchen.log';
    },
    ...overrides,
  });
}

function makeConfig(): AppConfig {
  return {
    isDev: false,
    isMac: false,
    ports: { corePort: 4242, colibriPort: 4343, mcpPort: 4445, proxyPort: 4141 },
    apiUrl: '',
  } satisfies AppConfig;
}

describe('starlingHandler', () => {
  beforeEach(() => {
    osState.platform = 'linux';
    osState.release = '5.0.0';
    buildStarlingInvocationMock.mockReset();
    buildStarlingInvocationMock.mockReturnValue({ command: 'starling', args: [] });
    selectPortMock.mockReset();
    selectPortMock.mockImplementation(async (port: number) => port);
    spawnMock.mockReset();
    findUnusableBinaryMock.mockReset();
    findUnusableBinaryMock.mockReturnValue(undefined);
    refusedStarlingMock.mockReset();
    refusedStarlingMock.mockReturnValue(undefined);
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should drive the initial bring-up via the start request and collapse the renderer onto the proxy origin', async () => {
    const methods: string[] = [];
    const child = makeFakeChild((message, stdout) => {
      if (message.method)
        methods.push(message.method);
      writeMessage(stdout, { id: message.id, result: null });
    });
    spawnMock.mockImplementation(() => child);
    const config = makeConfig();
    const handler = new StarlingHandler(makeLogger(), config);
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(spawnMock).toHaveBeenCalledTimes(1);
    expect(methods).toContain(StarlingMethod.START); // renderer drives the first bring-up
    expect(onProcessError).not.toHaveBeenCalled();
    // Single-origin posture: the renderer gets only the proxy origin, with colibri under /colibri.
    expect(config.apiUrl).toBe('http://127.0.0.1:4141');
    expect(handler.getMcpServerEndpoint()).toBe('http://127.0.0.1:4445/mcp');
    expect(selectPortMock).toHaveBeenCalledWith(4242, '127.0.0.1');
    expect(selectPortMock).toHaveBeenCalledWith(4343, '127.0.0.1');
    expect(selectPortMock).toHaveBeenCalledWith(4445, '127.0.0.1');
    expect(selectPortMock).toHaveBeenCalledWith(4141, '127.0.0.1');
    expect(buildStarlingInvocationMock).toHaveBeenCalledWith(
      expect.objectContaining({ mcpPort: 4445, proxyPort: 4141 }),
    );
  });

  it('should not name a core upstream when no dev-proxy was started', async () => {
    spawnMock.mockImplementation(() => makeFakeChild(nullResponder));
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    await handler.restartBackend({}, { onProcessError: vi.fn() });

    expect(buildStarlingInvocationMock).toHaveBeenCalledWith(
      expect.objectContaining({ coreUpstreamPort: undefined }),
    );
  });

  it('should pass the dev-proxy port through to starling when one was started', async () => {
    spawnMock.mockImplementation(() => makeFakeChild(nullResponder));
    const config = makeConfig();
    const handler = new StarlingHandler(
      makeLogger(),
      { ...config, ports: { ...config.ports, coreUpstreamPort: 4243 } },
    );

    await handler.restartBackend({}, { onProcessError: vi.fn() });

    expect(buildStarlingInvocationMock).toHaveBeenCalledWith(
      expect.objectContaining({ coreUpstreamPort: 4243, corePort: 4242 }),
    );
  });

  it('should refuse to start when core cannot bind the port the dev-proxy forwards to, rather than leave the proxy pointed at nothing', async () => {
    selectPortMock.mockImplementation(async (port: number) => port === 4242 ? 4250 : port);
    spawnMock.mockImplementation(() => makeFakeChild(nullResponder));
    const config = makeConfig();
    const handler = new StarlingHandler(
      makeLogger(),
      { ...config, ports: { ...config.ports, coreUpstreamPort: 4243 } },
    );
    const onProcessError = vi.fn();

    await handler.restartBackend({}, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith(expect.stringContaining('4242'), BackendCode.TERMINATED);
    expect(spawnMock).not.toHaveBeenCalled();
  });

  it('should still let core move to a free port when no dev-proxy is in the chain', async () => {
    selectPortMock.mockImplementation(async (port: number) => port === 4242 ? 4250 : port);
    spawnMock.mockImplementation(() => makeFakeChild(nullResponder));
    const onProcessError = vi.fn();

    await new StarlingHandler(makeLogger(), makeConfig()).restartBackend({}, { onProcessError });

    expect(onProcessError).not.toHaveBeenCalled();
    expect(buildStarlingInvocationMock).toHaveBeenCalledWith(expect.objectContaining({ corePort: 4250 }));
  });

  it('should publish and launch MCP on an available port', async () => {
    selectPortMock.mockImplementation(async (port: number) => port === 4445 ? 4450 : port);
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    await handler.restartBackend({}, { onProcessError: vi.fn() });

    expect(handler.getMcpServerEndpoint()).toBe('http://127.0.0.1:4450/mcp');
    expect(buildStarlingInvocationMock).toHaveBeenCalledWith(
      expect.objectContaining({ mcpPort: 4450 }),
    );
  });

  it('should forward the MCP auto-start option during initial bring-up', async () => {
    let startParams: Record<string, unknown> | undefined;
    const child = makeFakeChild((message, stdout) => {
      if (message.method === StarlingMethod.START)
        startParams = message.params;
      writeMessage(stdout, { id: message.id, result: null });
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    await handler.restartBackend({ mcpAutoStart: true }, { onProcessError: vi.fn() });

    expect(startParams).toMatchObject({ mcpAutoStart: true });
  });

  it('should start and stop MCP independently through starling', async () => {
    let mcpState: StarlingServiceStatus = StarlingServiceStatus.IDLE;
    const methods: string[] = [];
    const child = makeFakeChild((message, stdout) => {
      if (message.method)
        methods.push(message.method);
      if (message.method === StarlingMethod.START_SERVICE)
        mcpState = StarlingServiceStatus.READY;
      else if (message.method === StarlingMethod.STOP_SERVICE)
        mcpState = StarlingServiceStatus.STOPPED;

      const result = message.method === StarlingMethod.STATUS
        ? {
            services: [
              { name: StarlingService.CORE, state: StarlingServiceStatus.READY },
              { name: StarlingService.MCP, state: mcpState },
            ],
          }
        : null;
      writeMessage(stdout, { id: message.id, result });
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    await handler.restartBackend({}, { onProcessError: vi.fn() });

    expect(await handler.setMcpServerRunning(true)).toBe(StarlingServiceStatus.READY);
    expect(await handler.setMcpServerRunning(false)).toBe(StarlingServiceStatus.STOPPED);
    expect(methods).toContain(StarlingMethod.START_SERVICE);
    expect(methods).toContain(StarlingMethod.STOP_SERVICE);
  });

  it('should restart a live MCP service to clear its session on logout', async () => {
    let mcpState: StarlingServiceStatus = StarlingServiceStatus.READY;
    const methods: string[] = [];
    const child = makeFakeChild((message, stdout) => {
      if (message.method)
        methods.push(message.method);
      if (message.method === StarlingMethod.STOP_SERVICE)
        mcpState = StarlingServiceStatus.STOPPED;
      else if (message.method === StarlingMethod.START_SERVICE)
        mcpState = StarlingServiceStatus.READY;

      const result = message.method === StarlingMethod.STATUS
        ? { services: [{ name: StarlingService.MCP, state: mcpState }] }
        : null;
      writeMessage(stdout, { id: message.id, result });
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    await handler.restartBackend({}, { onProcessError: vi.fn() });

    await handler.resetMcpSession();

    expect(methods.filter(method => method === StarlingMethod.STOP_SERVICE)).toHaveLength(1);
    expect(methods.filter(method => method === StarlingMethod.START_SERVICE)).toHaveLength(1);
    expect(methods.indexOf(StarlingMethod.STOP_SERVICE)).toBeLessThan(methods.indexOf(StarlingMethod.START_SERVICE));
  });

  it('should preserve an intentionally stopped MCP service on logout', async () => {
    const methods: string[] = [];
    const child = makeFakeChild((message, stdout) => {
      if (message.method)
        methods.push(message.method);
      const result = message.method === StarlingMethod.STATUS
        ? { services: [{ name: StarlingService.MCP, state: StarlingServiceStatus.STOPPED }] }
        : null;
      writeMessage(stdout, { id: message.id, result });
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    await handler.restartBackend({}, { onProcessError: vi.fn() });

    await handler.resetMcpSession();

    expect(methods).not.toContain(StarlingMethod.STOP_SERVICE);
    expect(methods).not.toContain(StarlingMethod.START_SERVICE);
  });

  it('should report MCP as unavailable when starling is not running', async () => {
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    expect(await handler.getMcpServerState()).toBe(StarlingServiceStatus.UNAVAILABLE);
    expect(await handler.setMcpServerRunning(true)).toBe(StarlingServiceStatus.UNAVAILABLE);
    expect(await handler.setMcpServerRunning(false)).toBe(StarlingServiceStatus.UNAVAILABLE);
  });

  it('should map an unsupported macOS version to MACOS_VERSION', async () => {
    osState.platform = 'darwin';
    osState.release = '16.0.0'; // darwin 17 == High Sierra; 16 is too old
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith('rotki requires at least macOS High Sierra', BackendCode.MACOS_VERSION);
    expect(spawnMock).not.toHaveBeenCalled();
  });

  it('should map Windows 8.1 (release 6.3), below the Windows 10 floor, to WIN_VERSION', async () => {
    osState.platform = 'win32';
    osState.release = '6.3.9600';
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith('rotki requires at least Windows 10', BackendCode.WIN_VERSION);
    expect(spawnMock).not.toHaveBeenCalled();
  });

  it('should map a crash event to a TERMINATED process error', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => emitReady(child));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    writeMessage(child.stdout, { method: StarlingEvent.CRASHED, params: { lastError: 'core died' } });

    await vi.waitFor(() => expect(onProcessError).toHaveBeenCalledWith('core died', BackendCode.TERMINATED));
  });

  it('should refuse to spawn when a bundled binary is gone, and name it', async () => {
    findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(spawnMock).not.toHaveBeenCalled();
    expect(onProcessError).toHaveBeenCalledWith(
      expect.stringContaining(QUARANTINED_COLIBRI.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_COLIBRI,
    );
  });

  it('should blame the missing binary rather than the crash when a service dies with exit code 0 and its file gone', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => emitReady(child));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
    writeMessage(child.stdout, { method: StarlingEvent.CRASHED, params: { lastError: 'exited code Some(0)' } });

    await vi.waitFor(() => expect(onProcessError).toHaveBeenCalledWith(
      expect.stringContaining(QUARANTINED_COLIBRI.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_COLIBRI,
    ));
    expect(onProcessError).not.toHaveBeenCalledWith('exited code Some(0)', BackendCode.TERMINATED);
  });

  it('should blame the missing binary when starling itself exits non-zero', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
      queueMicrotask(() => child.emit('exit', 1, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith(
      expect.stringContaining(QUARANTINED_COLIBRI.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_COLIBRI,
    );
    expect(onProcessError).toHaveBeenCalledTimes(1);
  });

  it('should blame the missing binary when starling is killed with exit code 0 and its file is gone', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      findUnusableBinaryMock.mockReturnValue(QUARANTINED_STARLING);
      queueMicrotask(() => child.emit('exit', 0, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith(
      expect.stringContaining(QUARANTINED_STARLING.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_STARLING,
    );
    expect(onProcessError).toHaveBeenCalledTimes(1);
  });

  it('should report the binary when antivirus takes the file only after the generic failure was shown', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 1, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    expect(onProcessError).toHaveBeenLastCalledWith(expect.any(String), BackendCode.TERMINATED);

    findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
    vi.advanceTimersByTime(2000);

    expect(onProcessError).toHaveBeenLastCalledWith(
      expect.stringContaining(QUARANTINED_COLIBRI.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_COLIBRI,
    );
    vi.advanceTimersByTime(20_000);
    expect(onProcessError).toHaveBeenCalledTimes(2);
  });

  it('should stop looking for a lost binary after a few checks when every file stays put', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 1, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError: vi.fn() });
    const checksBefore = findUnusableBinaryMock.mock.calls.length;
    vi.advanceTimersByTime(60_000);

    expect(findUnusableBinaryMock.mock.calls.length - checksBefore).toBe(5);
  });

  it('should not report exit code 0 with every file in place, since that is how starling ends on logoff or Ctrl+C', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 0, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    vi.advanceTimersByTime(60_000);

    expect(findUnusableBinaryMock.mock.calls.length).toBeGreaterThan(2);
    expect(onProcessError).not.toHaveBeenCalled();
  });

  it('should keep watching after exit code 0, since antivirus can kill with it and quarantine the file a moment later', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 0, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    expect(onProcessError).not.toHaveBeenCalled();
    findUnusableBinaryMock.mockReturnValue(QUARANTINED_STARLING);
    vi.advanceTimersByTime(2000);

    expect(onProcessError).toHaveBeenCalledExactlyOnceWith(
      expect.stringContaining(QUARANTINED_STARLING.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_STARLING,
    );
  });

  it('should end the watch started by exit code 0 when rotki quits', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 0, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    await handler.stop();
    findUnusableBinaryMock.mockReturnValue(QUARANTINED_STARLING);
    vi.advanceTimersByTime(20_000);

    expect(onProcessError).not.toHaveBeenCalled();
  });

  it('should report a lost binary once when a crash is followed by starling\'s own exit', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => emitReady(child));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
    writeMessage(child.stdout, { method: StarlingEvent.CRASHED, params: { service: 'colibri', lastError: 'exited with code 1' } });
    await vi.waitFor(() => expect(onProcessError).toHaveBeenCalled());
    child.emit('exit', 1, null);
    await vi.waitFor(() => expect(findUnusableBinaryMock.mock.calls.length).toBeGreaterThanOrEqual(2));

    expect(onProcessError).toHaveBeenCalledExactlyOnceWith(
      expect.stringContaining(QUARANTINED_COLIBRI.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_COLIBRI,
    );
  });

  it('should name the crashed service in the generic message', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => emitReady(child));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    writeMessage(child.stdout, { method: StarlingEvent.CRASHED, params: { service: 'core', lastError: 'exited with code 1' } });

    await vi.waitFor(() => expect(onProcessError).toHaveBeenCalledWith(
      'The rotki backend service \'core\' stopped unexpectedly (exited with code 1). Please check the logs for more details.',
      BackendCode.TERMINATED,
    ));
  });

  it('should report starling as blocked when the system refuses to spawn a file that is there', async () => {
    const blocked: UnusableBinary = { ...QUARANTINED_STARLING, status: BinaryStatus.NOT_EXECUTABLE };
    const refusal = Object.assign(new Error('spawn EPERM'), { code: 'EPERM', syscall: 'spawn' });
    spawnMock.mockImplementation(() => {
      throw refusal;
    });
    refusedStarlingMock.mockImplementation(error => (error === refusal ? blocked : undefined));
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledExactlyOnceWith(
      expect.stringContaining(blocked.path),
      BackendCode.MISSING_BINARY,
      blocked,
    );
  });

  it('should keep a crash\'s own reason rather than bury it under the generic text of the exit that follows', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => emitReady(child));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    writeMessage(child.stdout, { method: StarlingEvent.CRASHED, params: { lastError: 'core died: disk full' } });
    await vi.waitFor(() => expect(onProcessError).toHaveBeenCalledWith('core died: disk full', BackendCode.TERMINATED));
    child.emit('exit', 1, null);
    await vi.waitFor(() => expect(findUnusableBinaryMock.mock.calls.length).toBeGreaterThanOrEqual(3));

    expect(onProcessError).toHaveBeenCalledTimes(1);
  });

  it('should check the core binary starling was launched with', async () => {
    buildStarlingInvocationMock.mockReturnValue({
      command: 'starling',
      args: ['--core-binary', '/opt/rotki/resources/backend/rotki-core/rotki-core-1.44.0'],
    });
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => emitReady(child));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError: vi.fn() });

    expect(findUnusableBinaryMock).toHaveBeenCalledWith('/opt/rotki/resources/backend/rotki-core/rotki-core-1.44.0');
  });

  it('should end a running watch when the backend is restarted in place', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => emitReady(child));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    writeMessage(child.stdout, { method: StarlingEvent.CRASHED, params: { lastError: 'core died' } });
    await vi.waitFor(() => expect(onProcessError).toHaveBeenCalledWith('core died', BackendCode.TERMINATED));
    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
    vi.advanceTimersByTime(20_000);

    expect(onProcessError).not.toHaveBeenCalledWith(expect.anything(), BackendCode.MISSING_BINARY, expect.anything());
  });

  it('should keep watching for a lost binary after a rejected start tears the tree down', async () => {
    const child = makeFakeChild((message, stdout) => {
      if (message.method === StarlingMethod.START) {
        writeMessage(stdout, { id: message.id, error: { message: 'service \'colibri\' could not be started' } });
        return;
      }
      writeMessage(stdout, { id: message.id, result: null });
      if (message.method === 'stop')
        queueMicrotask(() => child.emit('exit', 0, null));
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    expect(onProcessError).toHaveBeenLastCalledWith('service \'colibri\' could not be started', BackendCode.TERMINATED);

    findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
    vi.advanceTimersByTime(2000);

    expect(onProcessError).toHaveBeenLastCalledWith(
      expect.stringContaining(QUARANTINED_COLIBRI.path),
      BackendCode.MISSING_BINARY,
      QUARANTINED_COLIBRI,
    );
  });

  it('should report a spawn that throws instead of letting it escape the listener', async () => {
    spawnMock.mockImplementation(() => {
      throw Object.assign(new Error('spawn UNKNOWN'), { code: 'UNKNOWN' });
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await expect(handler.restartBackend({ dataDirectory: '/data' }, { onProcessError })).resolves.toBeUndefined();

    expect(onProcessError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'spawn UNKNOWN' }),
      BackendCode.TERMINATED,
    );
  });

  it('should end the watch on a deliberate stop even once the child is gone, so an update cannot trip it', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 1, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });
    await handler.stop();
    findUnusableBinaryMock.mockReturnValue(QUARANTINED_COLIBRI);
    vi.advanceTimersByTime(20_000);

    expect(onProcessError).not.toHaveBeenCalledWith(expect.anything(), BackendCode.MISSING_BINARY, expect.anything());
  });

  it('should keep the generic crash message when every binary is still there', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 1, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith(
      'The rotki backend stopped unexpectedly. Please check the logs for more details.',
      BackendCode.TERMINATED,
    );
  });

  it('should report a core binary that cannot be resolved instead of throwing past the listener', async () => {
    buildStarlingInvocationMock.mockImplementation(() => {
      throw new Error('No rotki-core binary found under /opt/rotki/resources/backend');
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await expect(handler.restartBackend({ dataDirectory: '/data' }, { onProcessError })).resolves.toBeUndefined();

    expect(spawnMock).not.toHaveBeenCalled();
    expect(onProcessError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'No rotki-core binary found under /opt/rotki/resources/backend' }),
      BackendCode.TERMINATED,
    );
  });

  it('should not treat an MCP crash as a backend crash', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onMcpState = vi.fn();
    const onProcessError = vi.fn();

    await handler.restartBackend({}, { onMcpState, onProcessError });
    writeMessage(child.stdout, {
      method: StarlingEvent.CRASHED,
      params: { lastError: 'mcp died', service: StarlingService.MCP },
    });
    await new Promise<void>(resolve => queueMicrotask(() => resolve()));

    expect(onMcpState).toHaveBeenCalledWith(StarlingServiceStatus.FAILED);
    expect(onProcessError).not.toHaveBeenCalled();
  });

  it('should handle every lifecycle event starling can push', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => child);
    const debug = vi.fn();
    const info = vi.fn();
    const handler = new StarlingHandler(makeLogger({ debug, info }), makeConfig());

    await handler.restartBackend({}, { onProcessError: vi.fn() });
    // The crash event has its own tests; for the rest the log line is the only evidence of routing.
    for (const method of [StarlingEvent.READY, StarlingEvent.RESTARTING, StarlingEvent.STOPPED])
      writeMessage(child.stdout, { method });
    writeMessage(child.stdout, { method: 'event.unknown' });

    await vi.waitFor(() => expect(debug).toHaveBeenCalledWith('Unhandled control event: event.unknown'));
    expect(info).toHaveBeenCalledWith(`Backend event: ${StarlingEvent.READY}`);
    expect(info).toHaveBeenCalledWith(`Backend event: ${StarlingEvent.RESTARTING}`);
    expect(info).toHaveBeenCalledWith(`Backend event: ${StarlingEvent.STOPPED}`);
  });

  it('should surface the data-dir-in-use exit code as a TERMINATED error', async () => {
    const child = makeFakeChild(nullResponder);
    // Exit before readiness completes: starling could not acquire the data-dir lock.
    spawnMock.mockImplementation(() => {
      queueMicrotask(() => child.emit('exit', 3, null));
      return child;
    });
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith(
      'Another rotki instance is already using this data directory. Please close it and try again.',
      BackendCode.TERMINATED,
    );
    // The exit reason is reported once; the readiness path must not double it.
    expect(onProcessError).toHaveBeenCalledTimes(1);
  });

  it('should surface the dead core\'s own text when a supervising starling rejects the start', async () => {
    const reason = 'failed to start the backend: service \'core\' exited before becoming ready: '
      + 'ERROR at initialization: Tables {\'asset_flags\'} are missing from your global database';
    const child = makeFakeChild((message, stdout) => {
      if (message.method === StarlingMethod.START) {
        writeMessage(stdout, { id: message.id, error: { message: reason } });
        return;
      }
      // Answer `stop` and let the child exit so teardown does not hit the kill timeout.
      writeMessage(stdout, { id: message.id, result: null });
      if (message.method === 'stop')
        queueMicrotask(() => child.emit('exit', 0, null));
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onProcessError = vi.fn();

    await handler.restartBackend({ dataDirectory: '/data' }, { onProcessError });

    expect(onProcessError).toHaveBeenCalledWith(reason, BackendCode.TERMINATED);
    expect(onProcessError).toHaveBeenCalledTimes(1);
  });
});
