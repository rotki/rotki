import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const mockHandleMessage = vi.fn();
const mockDelay = vi.fn();
const mockLoggerDebug = vi.fn();
const mockLoggerError = vi.fn();

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: {
    serverUrl: 'http://localhost:4242',
  },
}));

vi.mock('@/modules/core/messaging', () => ({
  useMessageHandling: vi.fn((): { handleMessage: typeof mockHandleMessage } => ({
    handleMessage: mockHandleMessage,
  })),
}));

vi.mock('@/modules/core/common/async/async-utilities', () => ({
  delay: async (...args: unknown[]): Promise<void> => mockDelay(...args),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    debug: (...args: unknown[]): void => mockLoggerDebug(...args),
    error: (...args: unknown[]): void => mockLoggerError(...args),
    info: vi.fn(),
  },
}));

type EventHandler = (...args: unknown[]) => void;

interface MockWebSocketInstance {
  addEventListener: (event: string, handler: EventHandler) => void;
  close: ReturnType<typeof vi.fn>;
  listeners: Record<string, EventHandler[]>;
  onerror: (() => void) | null;
  onmessage: ((event: { data: string }) => void) | null;
  triggerClose: (wasClean: boolean) => void;
  triggerError: () => void;
  triggerOpen: () => void;
}

let latestMockWs: MockWebSocketInstance | null = null;

function createMockWebSocket(): MockWebSocketInstance {
  const listeners: Record<string, EventHandler[]> = {};
  const ws: MockWebSocketInstance = {
    addEventListener(event: string, handler: EventHandler): void {
      if (!listeners[event])
        listeners[event] = [];

      listeners[event].push(handler);
    },
    close: vi.fn(),
    listeners,
    onerror: null,
    onmessage: null,
    triggerClose(wasClean: boolean): void {
      for (const handler of listeners.close ?? [])
        handler({ wasClean });
    },
    triggerError(): void {
      if (ws.onerror)
        ws.onerror();
    },
    triggerOpen(): void {
      for (const handler of listeners.open ?? [])
        handler();
    },
  };
  return ws;
}

// Use a class-based mock so `new WebSocket()` works correctly
class MockWebSocket {
  constructor() {
    const ws = createMockWebSocket();
    latestMockWs = ws;
    return ws;
  }
}

async function loadComposable(): Promise<typeof import('./use-websocket-connection')> {
  vi.doUnmock('@/modules/shell/app/use-websocket-connection');
  vi.resetModules();
  return import('./use-websocket-connection');
}

describe('useWebsocketConnection', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockDelay.mockResolvedValue(undefined);
    latestMockWs = null;
    vi.stubGlobal('WebSocket', MockWebSocket);
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('should create a WebSocket connection and resolve true on open', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect, connected } = useWebsocketConnection();

      const connectPromise = connect();

      expect(latestMockWs).not.toBeNull();
      latestMockWs?.triggerOpen();

      const result = await connectPromise;
      expect(result).toBe(true);
      expect(get(connected)).toBe(true);
    });
  });

  it('should resolve false when connection is disabled', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect, setConnectionEnabled } = useWebsocketConnection();

      setConnectionEnabled(false);

      const result = await connect();
      expect(result).toBe(false);
      expect(latestMockWs).toBeNull();
    });
  });

  it('should resolve true immediately if already connected', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect } = useWebsocketConnection();

      const firstPromise = connect();
      latestMockWs?.triggerOpen();
      await firstPromise;

      latestMockWs = null;

      const result = await connect();
      expect(result).toBe(true);
      // Should not have created a new WebSocket
      expect(latestMockWs).toBeNull();
    });
  });

  it('should close existing connection on disconnect', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect, disconnect } = useWebsocketConnection();

      const connectPromise = connect();
      const ws = latestMockWs;
      ws?.triggerOpen();
      await connectPromise;

      disconnect();
      expect(ws?.close).toHaveBeenCalledOnce();
      expect(mockLoggerDebug).toHaveBeenCalledWith('websocket was disconnected');
    });
  });

  it('should log when no connection exists on disconnect', async () => {
    const { useWebsocketConnection } = await loadComposable();

    scope.run(() => {
      const { disconnect } = useWebsocketConnection();

      disconnect();
      expect(mockLoggerDebug).toHaveBeenCalledWith('websocket was not connected');
    });
  });

  it('should disconnect and block future connections when disabled', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect, setConnectionEnabled } = useWebsocketConnection();

      const connectPromise = connect();
      const ws = latestMockWs;
      ws?.triggerOpen();
      await connectPromise;

      setConnectionEnabled(false);
      expect(ws?.close).toHaveBeenCalledOnce();
      expect(mockLoggerDebug).toHaveBeenCalledWith('Websocket connections disabled');

      const result = await connect();
      expect(result).toBe(false);
    });
  });

  it('should re-enable connections after being disabled', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect, setConnectionEnabled } = useWebsocketConnection();

      setConnectionEnabled(false);

      const blockedResult = await connect();
      expect(blockedResult).toBe(false);

      setConnectionEnabled(true);
      expect(mockLoggerDebug).toHaveBeenCalledWith('Websocket connections enabled');

      const connectPromise = connect();
      latestMockWs?.triggerOpen();
      const result = await connectPromise;
      expect(result).toBe(true);
    });
  });

  it('should resolve false on WebSocket error', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect, connected } = useWebsocketConnection();

      const connectPromise = connect();
      latestMockWs?.triggerError();

      const result = await connectPromise;
      expect(result).toBe(false);
      expect(get(connected)).toBe(false);
      expect(mockLoggerError).toHaveBeenCalledWith('websocket connection failed');
    });
  });

  it('should attempt reconnect on unclean close', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect } = useWebsocketConnection();

      const connectPromise = connect();
      latestMockWs?.triggerOpen();
      await connectPromise;

      latestMockWs?.triggerClose(false);

      expect(mockDelay).toHaveBeenCalledWith(2000);
    });
  });

  it('should not attempt reconnect on clean close', async () => {
    const { useWebsocketConnection } = await loadComposable();

    await scope.run(async () => {
      const { connect } = useWebsocketConnection();

      const connectPromise = connect();
      latestMockWs?.triggerOpen();
      await connectPromise;

      latestMockWs?.triggerClose(true);

      expect(mockDelay).not.toHaveBeenCalled();
    });
  });
});
