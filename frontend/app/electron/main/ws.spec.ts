// @vitest-environment node
import type { LogService } from '@electron/main/log-service';
import { EventEmitter } from 'node:events';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { IDLE_TIMEOUT_MS, IPC_CONNECTION_STATUS_CHANNEL, type WalletBridgeIpcCallbacks } from './wallet-bridge-ws-types';
import { WalletBridgeWebSocketServer } from './ws';

const { servers } = vi.hoisted(() => {
  const servers: EventEmitter[] = [];
  return { servers };
});

vi.mock('ws', async () => {
  const { EventEmitter } = await import('node:events');

  class WebSocketServer extends EventEmitter {
    readonly clients = new Set<unknown>();

    constructor() {
      super();
      servers.push(this);
      queueMicrotask(() => this.emit('listening'));
    }

    close(callback?: () => void): void {
      callback?.();
    }
  }

  return { WebSocketServer };
});

class FakeSocket extends EventEmitter {
  readonly OPEN = 1;
  readyState = 1;
  readonly sent: string[] = [];

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = 3;
  }

  terminate(): void {
    this.readyState = 3;
  }

  respond(id: string, result: unknown): void {
    this.emit('message', JSON.stringify({ id, jsonrpc: '2.0', result }));
  }
}

function lastRequestId(socket: FakeSocket): string {
  const request: unknown = JSON.parse(socket.sent.at(-1) ?? '{}');
  const id = typeof request === 'object' && request !== null ? Reflect.get(request, 'id') : undefined;
  return String(id);
}

async function startServer(): Promise<{ server: WalletBridgeWebSocketServer; connect: () => FakeSocket }> {
  const server = new WalletBridgeWebSocketServer(createMock<LogService>({
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  }));
  await server.start(40011);
  const wss = servers.at(-1)!;
  return {
    connect: (): FakeSocket => {
      const socket = new FakeSocket();
      wss.emit('connection', socket);
      return socket;
    },
    server,
  };
}

describe('electron/main/ws', () => {
  beforeEach(() => {
    servers.length = 0;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should keep the idle timer of the new connection when the superseded socket closes', async () => {
    const { connect } = await startServer();
    vi.useFakeTimers();
    const first = connect();
    const second = connect();

    first.emit('close');
    vi.advanceTimersByTime(IDLE_TIMEOUT_MS);

    expect(second.readyState).toBe(3);
  });

  it('should not extend the idle timer of the new connection on a message from the superseded socket', async () => {
    const { connect } = await startServer();
    vi.useFakeTimers();
    const first = connect();
    const second = connect();

    vi.advanceTimersByTime(IDLE_TIMEOUT_MS - 1);
    first.respond('stale', '0x1');
    vi.advanceTimersByTime(1);

    expect(second.readyState).toBe(3);
  });

  it('should reject a request whose response arrives after its connection was replaced', async () => {
    const { connect, server } = await startServer();
    const first = connect();
    const request = server.sendToWalletBridge({ method: 'eth_chainId', params: [] });
    const requestId = lastRequestId(first);

    // Not OPEN, so the takeover does not cancel the first connection's requests itself.
    first.readyState = 2;
    connect();
    first.respond(requestId, '0x1');

    await expect(request).rejects.toThrow('was replaced');
  });

  it('should resolve a response from the active connection', async () => {
    const { connect, server } = await startServer();
    const socket = connect();
    const request = server.sendToWalletBridge({ method: 'eth_chainId', params: [] });

    socket.respond(lastRequestId(socket), '0x1');

    await expect(request).resolves.toBe('0x1');
  });

  it('should keep a live connection when the ipc callbacks are set after it connected', async () => {
    const { connect, server } = await startServer();
    const socket = connect();
    const sendIpcMessage = vi.fn<WalletBridgeIpcCallbacks['sendIpcMessage']>();

    server.setIpcCallbacks({ sendIpcMessage });
    expect(server.isConnected()).toBe(true);

    socket.emit('close');
    expect(sendIpcMessage).toHaveBeenCalledWith(IPC_CONNECTION_STATUS_CHANNEL, 'disconnected');
  });
});
