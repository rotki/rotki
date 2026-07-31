import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import { EventEmitter } from 'node:events';
import { PassThrough, Writable } from 'node:stream';
import { BackendCode } from '@shared/ipc';
import { LogLevel } from '@shared/log-level';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StarlingHandler } from './starling-handler';

// Mutable os identity the handler's version gates read through. Only the two
// identity calls are faked; the rest of the builtin stays real, since other
// modules in the graph (cargo-env) read it too.
const osState = { platform: 'linux', release: '5.0.0' };
vi.mock('node:os', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:os')>();
  const identity = {
    platform: (): string => osState.platform,
    release: (): string => osState.release,
  };
  return { ...actual, default: { ...actual, ...identity }, ...identity };
});

// `spawn` hands back whatever fake child the test installs; the rest of the
// builtin stays real (other modules in the graph rely on it). `vi.hoisted` keeps
// the mock fn defined before the hoisted vi.mock factory references it.
const { buildStarlingInvocationMock, selectPortMock, spawnMock } = vi.hoisted(() => ({
  buildStarlingInvocationMock: vi.fn(),
  selectPortMock: vi.fn(),
  spawnMock: vi.fn(),
}));
vi.mock('node:child_process', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:child_process')>();
  return { ...actual, default: { ...actual, spawn: spawnMock }, spawn: spawnMock };
});

// The invocation builder touches the filesystem / uv detection in real life —
// the handler only forwards its result to spawn(), so a stub is enough. The rest
// of the module stays real: SHUTDOWN_GRACE_SECS is what the handler derives its
// stop timeouts from, and a stubbed-away value would make those NaN.
vi.mock('@shared/starling/starling-args', async importOriginal => ({
  ...await importOriginal<typeof import('@shared/starling/starling-args')>(),
  buildStarlingInvocation: buildStarlingInvocationMock,
}));

vi.mock('@electron/main/port-utils', () => ({
  selectPort: selectPortMock,
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
  writeMessage(child.stdout, { method: 'event.ready', params: { services: ['core', 'colibri'] } });
}

function makeLogger(): LogService {
  return createMock<LogService>({
    getLogLevel: vi.fn(() => LogLevel.INFO),
    get coreProcessLogPath(): string {
      return '/tmp/logs/rotkehlchen.log';
    },
  });
}

function makeConfig(): AppConfig {
  return {
    isDev: false,
    isMac: false,
    ports: { corePort: 4242, colibriPort: 4343, mcpPort: 4445, proxyPort: 4141 },
    urls: { coreApiUrl: '', colibriApiUrl: '' },
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
  });

  it('should drive the initial bring-up via the start request and collapse the renderer onto the proxy origin', async () => {
    // starling boots idle; the handler drives the first start and resolves on
    // its reply (not on an event), so record which control methods it sends.
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
    expect(methods).toContain('start'); // renderer drives the first bring-up
    expect(onProcessError).not.toHaveBeenCalled();
    // Single-origin posture: both URLs point at the proxy port; colibri sits
    // under /colibri. The direct core/colibri ports are the proxy's upstreams.
    expect(config.urls.coreApiUrl).toBe('http://127.0.0.1:4141');
    expect(config.urls.colibriApiUrl).toBe('http://127.0.0.1:4141/colibri');
    expect(handler.getMcpServerEndpoint()).toBe('http://127.0.0.1:4445/mcp');
    expect(selectPortMock).toHaveBeenCalledWith(4242, '127.0.0.1');
    expect(selectPortMock).toHaveBeenCalledWith(4343, '127.0.0.1');
    expect(selectPortMock).toHaveBeenCalledWith(4445, '127.0.0.1');
    expect(selectPortMock).toHaveBeenCalledWith(4141, '127.0.0.1');
    expect(buildStarlingInvocationMock).toHaveBeenCalledWith(
      expect.objectContaining({ mcpPort: 4445, proxyPort: 4141 }),
    );
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
      if (message.method === 'start')
        startParams = message.params;
      writeMessage(stdout, { id: message.id, result: null });
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    await handler.restartBackend({ mcpAutoStart: true }, { onProcessError: vi.fn() });

    expect(startParams).toMatchObject({ mcpAutoStart: true });
  });

  it('should start and stop MCP independently through starling', async () => {
    let mcpState = 'Idle';
    const methods: string[] = [];
    const child = makeFakeChild((message, stdout) => {
      if (message.method)
        methods.push(message.method);
      if (message.method === 'startService')
        mcpState = 'Ready';
      else if (message.method === 'stopService')
        mcpState = 'Stopped';

      const result = message.method === 'status'
        ? { services: [{ name: 'core', state: 'Ready' }, { name: 'mcp', state: mcpState }] }
        : null;
      writeMessage(stdout, { id: message.id, result });
    });
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    await handler.restartBackend({}, { onProcessError: vi.fn() });

    expect(await handler.setMcpServerRunning(true)).toBe('Ready');
    expect(await handler.setMcpServerRunning(false)).toBe('Stopped');
    expect(methods).toContain('startService');
    expect(methods).toContain('stopService');
  });

  it('should report MCP as unavailable when starling is not running', async () => {
    const handler = new StarlingHandler(makeLogger(), makeConfig());

    expect(await handler.getMcpServerState()).toBe('Unavailable');
    expect(await handler.setMcpServerRunning(true)).toBe('Unavailable');
    expect(await handler.setMcpServerRunning(false)).toBe('Unavailable');
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

  it('should map an unsupported Windows version to WIN_VERSION', async () => {
    osState.platform = 'win32';
    osState.release = '6.0.6000'; // < 6.1 (Windows 7)
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
    writeMessage(child.stdout, { method: 'event.crashed', params: { lastError: 'core died' } });

    await vi.waitFor(() => expect(onProcessError).toHaveBeenCalledWith('core died', BackendCode.TERMINATED));
  });

  it('should not treat an MCP crash as a backend crash', async () => {
    const child = makeFakeChild(nullResponder);
    spawnMock.mockImplementation(() => child);
    const handler = new StarlingHandler(makeLogger(), makeConfig());
    const onMcpState = vi.fn();
    const onProcessError = vi.fn();

    await handler.restartBackend({}, { onMcpState, onProcessError });
    writeMessage(child.stdout, {
      method: 'event.crashed',
      params: { lastError: 'mcp died', service: 'mcp' },
    });
    await new Promise<void>(resolve => queueMicrotask(() => resolve()));

    expect(onMcpState).toHaveBeenCalledWith('Failed');
    expect(onProcessError).not.toHaveBeenCalled();
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

  it('should surface the actual start-failure reason instead of a generic message', async () => {
    // starling stays alive (it supervises), but the `start` RPC rejects with the
    // dead core's own error text. The handler must relay that so the renderer's
    // error screen shows why it failed and the user can exit manually.
    const reason = 'failed to start the backend: service \'core\' exited before becoming ready: '
      + 'ERROR at initialization: Tables {\'asset_flags\'} are missing from your global database';
    const child = makeFakeChild((message, stdout) => {
      if (message.method === 'start') {
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
