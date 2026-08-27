import type { useControl as UseControl } from '@/modules/core/control/use-control';
import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { assert } from '@rotki/common';
import { StarlingServiceStatus } from '@shared/ipc';
import { StarlingService } from '@shared/starling/starling-protocol';
import { server } from '@test/setup-files/server';
import { createMock } from '@test/utils/create-mock';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  getMcpServerStatus: vi.fn(),
  isPackaged: false,
  restartBackend: vi.fn(),
  setMcpAutoStart: vi.fn(),
  startMcpServer: vi.fn(),
  stopMcpServer: vi.fn(),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): ReturnType<typeof useInterop> => createMock<ReturnType<typeof useInterop>>({ ...mocks }),
}));

const CONTROL_URL = 'http://localhost:3000/_control';

interface ControlFrame {
  method: string;
  params?: Record<string, unknown>;
}

function isControlFrame(value: unknown): value is ControlFrame {
  return typeof value === 'object' && value !== null && 'method' in value;
}

/**
 * The availability probe is cached for the life of the page, so every test needs
 * a module instance that has not probed yet.
 */
async function freshUseControl(): Promise<typeof UseControl> {
  vi.resetModules();
  return (await import('@/modules/core/control/use-control')).useControl;
}

function capabilities(): void {
  server.use(http.get(CONTROL_URL, () => HttpResponse.json({
    available: true,
    methods: ['health', 'status', 'restart', 'startService', 'stopService', 'setServiceAutostart'],
  })));
}

function statusReplying(state: StarlingServiceStatus): void {
  server.use(http.post(CONTROL_URL, () => HttpResponse.json({
    id: 1,
    jsonrpc: '2.0',
    result: {
      controlVersion: 1,
      services: [
        { autostart: true, name: 'core', restarts: 0, state: StarlingServiceStatus.READY },
        { autostart: false, name: 'mcp', restarts: 0, state },
      ],
    },
  })));
}

describe('modules/core/control/use-control', () => {
  beforeEach(() => {
    mocks.isPackaged = false;
    vi.clearAllMocks();
  });

  it('should report control as available when the endpoint answers the capability document', async () => {
    capabilities();
    const useControl = await freshUseControl();
    const { available, probe } = useControl();

    await expect(probe()).resolves.toBe(true);
    expect(get(available)).toBe(true);
  });

  it('should report control as unavailable when the endpoint is not mounted, so the app shows its blocked state rather than buttons', async () => {
    server.use(http.get(CONTROL_URL, () => new HttpResponse(null, { status: 404 })));
    const useControl = await freshUseControl();
    const { available, probe } = useControl();

    await expect(probe()).resolves.toBe(false);
    expect(get(available)).toBe(false);
  });

  it('should not attempt an operation when control is unavailable', async () => {
    server.use(http.get(CONTROL_URL, () => new HttpResponse(null, { status: 404 })));
    const post = vi.fn(() => HttpResponse.json({ id: 1, jsonrpc: '2.0', result: { ok: true } }));
    server.use(http.post(CONTROL_URL, post));

    const useControl = await freshUseControl();
    const { restart, serviceInfo, setServiceAutostart } = useControl();

    await restart();
    await expect(serviceInfo(StarlingService.MCP)).resolves.toEqual({
      autostart: false,
      state: StarlingServiceStatus.UNAVAILABLE,
    });
    await setServiceAutostart(StarlingService.MCP, true);
    expect(post).not.toHaveBeenCalled();
  });

  it('should read a service state and its auto-start preference out of the control status', async () => {
    capabilities();
    statusReplying(StarlingServiceStatus.READY);
    const useControl = await freshUseControl();

    await expect(useControl().serviceInfo(StarlingService.MCP)).resolves.toEqual({
      autostart: false,
      state: StarlingServiceStatus.READY,
    });
  });

  it('should report a service the supervisor does not know as unavailable', async () => {
    capabilities();
    server.use(http.post(CONTROL_URL, () => HttpResponse.json({
      id: 1,
      jsonrpc: '2.0',
      result: { controlVersion: 1, services: [] },
    })));
    const useControl = await freshUseControl();

    await expect(useControl().serviceInfo(StarlingService.MCP)).resolves.toEqual({
      autostart: false,
      state: StarlingServiceStatus.UNAVAILABLE,
    });
  });

  it('should send the auto-start preference as its own rpc, since routing it through restart would bounce core to record a preference', async () => {
    capabilities();
    const sent: ControlFrame[] = [];
    server.use(http.post(CONTROL_URL, async ({ request }) => {
      const body = await request.json();
      assert(isControlFrame(body), 'the client must send a JSON-RPC frame');
      sent.push(body);
      return HttpResponse.json({ id: 1, jsonrpc: '2.0', result: { ok: true } });
    }));

    const useControl = await freshUseControl();
    await useControl().setServiceAutostart(StarlingService.MCP, true);
    await useControl().setServiceAutostart(StarlingService.MCP, false);

    expect(sent.map(body => body.method)).toEqual(['setServiceAutostart', 'setServiceAutostart']);
    expect(sent[0].params).toEqual({ autostart: true, service: 'mcp' });
    expect(sent[1].params).toEqual({ autostart: false, service: 'mcp' });
  });

  it('should surface a refused auto-start write rather than reporting it as saved', async () => {
    capabilities();
    server.use(http.post(CONTROL_URL, () => HttpResponse.json({
      error: { code: -32000, message: 'failed to persist the autostart preference: read-only file system' },
      id: 1,
      jsonrpc: '2.0',
    })));

    const useControl = await freshUseControl();
    await expect(useControl().setServiceAutostart(StarlingService.MCP, true))
      .rejects
      .toThrow('failed to persist');
  });

  it('should send startService and stopService for the requested service', async () => {
    capabilities();
    const sent: ControlFrame[] = [];
    server.use(http.post(CONTROL_URL, async ({ request }) => {
      const body = await request.json();
      assert(isControlFrame(body), 'the client must send a JSON-RPC frame');
      sent.push(body);
      return HttpResponse.json({
        id: 1,
        jsonrpc: '2.0',
        result: body.method === 'status'
          ? { controlVersion: 1, services: [{ autostart: false, name: 'mcp', restarts: 0, state: StarlingServiceStatus.READY }] }
          : { ok: true },
      });
    }));

    const useControl = await freshUseControl();
    await useControl().setServiceRunning(StarlingService.MCP, true);
    await useControl().setServiceRunning(StarlingService.MCP, false);

    expect(sent.map(body => body.method)).toEqual(['startService', 'status', 'stopService', 'status']);
    expect(sent[0].params).toEqual({ service: 'mcp' });
    expect(sent[2].params).toEqual({ service: 'mcp' });
  });

  it('should surface a refused operation as an error rather than a silent success, since JSON-RPC reports a refusal in a 200 body', async () => {
    capabilities();
    server.use(http.post(CONTROL_URL, () => HttpResponse.json({
      error: { code: -32001, message: 'method \'stop\' is not permitted on the http-control transport' },
      id: 1,
      jsonrpc: '2.0',
    })));

    const useControl = await freshUseControl();
    await expect(useControl().restart()).rejects.toThrow('is not permitted');
  });

  it('should report a transport refusal with a translated message, since it carries no body to take one from', async () => {
    capabilities();
    server.use(http.post(CONTROL_URL, () => new HttpResponse(null, { status: 401 })));

    const useControl = await freshUseControl();
    await expect(useControl().restart()).rejects.toThrow('control.errors.unauthorized');
  });

  it('should distinguish an unreachable supervisor from a refused one', async () => {
    capabilities();
    server.use(http.post(CONTROL_URL, () => new HttpResponse(null, { status: 503 })));

    const useControl = await freshUseControl();
    await expect(useControl().restart()).rejects.toThrow('control.errors.unavailable');
  });

  it('should drive the desktop through electron rather than the http endpoint', async () => {
    mocks.isPackaged = true;
    mocks.startMcpServer.mockResolvedValue({ state: StarlingServiceStatus.READY });
    mocks.getMcpServerStatus.mockResolvedValue({ autoStart: true, endpoint: '', state: StarlingServiceStatus.READY });
    const post = vi.fn(() => HttpResponse.json({ id: 1, jsonrpc: '2.0', result: { ok: true } }));
    server.use(http.post(CONTROL_URL, post));

    const useControl = await freshUseControl();
    const { available, probe, restart, serviceInfo, setServiceAutostart, setServiceRunning, supportsOptions } = useControl();

    await expect(probe()).resolves.toBe(true);
    expect(get(available)).toBe(true);
    expect(supportsOptions).toBe(true);

    await expect(setServiceRunning(StarlingService.MCP, true)).resolves.toBe(StarlingServiceStatus.READY);
    expect(mocks.startMcpServer).toHaveBeenCalledOnce();

    await setServiceAutostart(StarlingService.MCP, false);
    expect(mocks.setMcpAutoStart).toHaveBeenCalledWith(false);
    await expect(serviceInfo(StarlingService.MCP)).resolves.toEqual({
      autostart: true,
      state: StarlingServiceStatus.READY,
    });

    await restart();
    expect(mocks.restartBackend).toHaveBeenCalledWith({}, true);
    expect(post).not.toHaveBeenCalled();
  });

  it('should report the desktop as the only runtime that takes restart options, even where auto-start is offered', async () => {
    capabilities();
    const useControl = await freshUseControl();
    expect(useControl().supportsOptions).toBe(false);
  });
});
