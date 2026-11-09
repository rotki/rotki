import type { WalletBridgeRequest, WalletBridgeResponse } from '@shared/wallet-bridge-types';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBridgeMessageHandlers } from '@/modules/wallet/bridge/use-bridge-message-handlers';
import { CLIENT_CONFIG } from './bridge-config';
import { BridgeConnectionPhase, useWalletProxyClient } from './use-wallet-proxy-client';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('@/modules/wallet/bridge/use-bridge-message-handlers', () => ({
  useBridgeMessageHandlers: vi.fn(),
}));

let handleRequest: (message: WalletBridgeRequest) => Promise<WalletBridgeResponse>;

/** Fires no events on its own: each test drives the lifecycle the way a browser would. */
class FakeWebSocket {
  static readonly OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  closeCalled = false;
  onopen?: (event: unknown) => void;
  onmessage?: (event: { data: string }) => void;
  onclose?: (event: unknown) => void;
  onerror?: (event: unknown) => void;
  readonly sent: string[] = [];

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.closeCalled = true;
    this.readyState = 3;
  }

  open(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.({});
  }

  /** A browser always follows `error` with `close`. */
  fail(): void {
    this.readyState = 3;
    this.onerror?.({});
    this.onclose?.({});
  }

  drop(): void {
    this.readyState = 3;
    this.onclose?.({});
  }

  receive(message: unknown): void {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
}

function lastSocket(): FakeWebSocket {
  return FakeWebSocket.instances.at(-1)!;
}

describe('modules/wallet/bridge/use-wallet-proxy-client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    FakeWebSocket.instances = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
    handleRequest = vi.fn<(message: WalletBridgeRequest) => Promise<WalletBridgeResponse>>(
      async () => ({ id: 1, jsonrpc: '2.0', result: '0x1' }),
    );
    vi.mocked(useBridgeMessageHandlers).mockReturnValue({ handleRequest });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('should be connecting until the socket opens, then connected', () => {
    const client = useWalletProxyClient();
    client.connect();
    expect(get(client.isConnecting)).toBe(true);

    lastSocket().open();
    expect(get(client.isConnected)).toBe(true);
    expect(get(client.isConnecting)).toBe(false);
    expect(lastSocket().url).toContain('/wallet-bridge');
  });

  it('should not open a second socket when connect is called while one is opening', () => {
    const client = useWalletProxyClient();
    client.connect();
    client.connect();

    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('should dispatch a request and send back the handler response', async () => {
    const client = useWalletProxyClient();
    client.connect();
    lastSocket().open();

    lastSocket().receive({ id: 1, jsonrpc: '2.0', method: 'eth_chainId' });
    await flushPromises();

    expect(handleRequest).toHaveBeenCalledWith(expect.objectContaining({ method: 'eth_chainId' }));
    expect(lastSocket().sent).toContainEqual(JSON.stringify({ id: 1, jsonrpc: '2.0', result: '0x1' }));
  });

  it('should close the tab on a close_tab notification', () => {
    const closeSpy = vi.spyOn(window, 'close').mockImplementation(() => {});
    const client = useWalletProxyClient();
    client.connect();
    lastSocket().open();

    lastSocket().receive({ type: 'close_tab' });
    expect(closeSpy).toHaveBeenCalledTimes(1);
  });

  it('should record the error message on socket error', () => {
    const client = useWalletProxyClient();
    client.connect();

    lastSocket().onerror?.({});
    expect(get(client.lastError)).toContain('WebSocket connection error');
  });

  describe('unparsable messages', () => {
    it('should answer a parse error when the invalid message shows an id', () => {
      const client = useWalletProxyClient();
      client.connect();
      lastSocket().open();

      lastSocket().receive({ id: 7, jsonrpc: '1.0', method: 'eth_chainId' });

      expect(lastSocket().sent).toEqual([
        JSON.stringify({ error: { code: -32700, message: 'Parse error' }, id: '7', jsonrpc: '2.0' }),
      ]);
      expect(handleRequest).not.toHaveBeenCalled();
    });

    it('should stay silent on an invalid message without an id', () => {
      const client = useWalletProxyClient();
      client.connect();
      lastSocket().open();

      lastSocket().receive({ foo: 'bar' });

      expect(lastSocket().sent).toEqual([]);
    });

    it('should stay silent on a frame that is not JSON, and keep handling later ones', async () => {
      const client = useWalletProxyClient();
      client.connect();
      lastSocket().open();

      lastSocket().onmessage?.({ data: '{"id":7,' });
      expect(lastSocket().sent).toEqual([]);

      lastSocket().receive({ id: 1, jsonrpc: '2.0', method: 'eth_chainId' });
      await flushPromises();
      expect(handleRequest).toHaveBeenCalledTimes(1);
    });
  });

  describe('disconnect', () => {
    it('should not reconnect after an intentional disconnect', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      const socket = lastSocket();
      socket.open();

      client.disconnect();
      expect(get(client.isConnected)).toBe(false);

      socket.drop();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY * 2);
      expect(FakeWebSocket.instances).toHaveLength(1);
      expect(get(client.state).phase).toBe(BridgeConnectionPhase.disconnected);
    });

    it('should close a socket that is still handshaking and ignore its late open', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      const socket = lastSocket();

      client.disconnect();
      expect(socket.closeCalled).toBe(true);

      socket.open();
      socket.drop();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY * 2);

      expect(get(client.isConnected)).toBe(false);
      expect(FakeWebSocket.instances).toHaveLength(1);
    });

    it('should cancel an already-scheduled reconnect', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      lastSocket().open();

      lastSocket().drop();
      client.disconnect();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY * 2);

      expect(FakeWebSocket.instances).toHaveLength(1);
    });
  });

  describe('retries', () => {
    it('should reconnect after an unexpected close', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      lastSocket().open();

      lastSocket().drop();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY);

      expect(FakeWebSocket.instances).toHaveLength(2);
    });

    it('should open exactly one retry socket when an attempt reports both error and close', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();

      lastSocket().fail();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY * 1.5);

      expect(FakeWebSocket.instances).toHaveLength(2);
    });

    it('should not read as connecting while waiting to retry', () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();

      lastSocket().fail();

      expect(get(client.isConnecting)).toBe(false);
      expect(get(client.state)).toEqual({ attempt: 1, phase: BridgeConnectionPhase.retryWaiting });
    });

    it('should stop after the maximum number of attempts', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();

      for (let attempt = 0; attempt < CLIENT_CONFIG.MAX_RETRIES; attempt++) {
        lastSocket().fail();
        await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY);
      }

      expect(FakeWebSocket.instances).toHaveLength(CLIENT_CONFIG.MAX_RETRIES);
      expect(get(client.state).phase).toBe(BridgeConnectionPhase.retriesExhausted);
    });

    it('should give a connection that dropped after opening a fresh retry budget', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();

      for (let attempt = 0; attempt < CLIENT_CONFIG.MAX_RETRIES - 1; attempt++) {
        lastSocket().fail();
        await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY);
      }
      lastSocket().open();
      lastSocket().drop();

      expect(get(client.state)).toEqual({ attempt: 1, phase: BridgeConnectionPhase.retryWaiting });
    });

    it('should fail a handshake that never finishes, close it and retry', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      const socket = lastSocket();

      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.HANDSHAKE_TIMEOUT);

      expect(socket.closeCalled).toBe(true);
      expect(get(client.lastError)).toContain('timed out');
      expect(get(client.state)).toEqual({ attempt: 1, phase: BridgeConnectionPhase.retryWaiting });

      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY);
      expect(FakeWebSocket.instances).toHaveLength(2);
    });

    it('should not time out a socket that opened in time', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      lastSocket().open();

      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.HANDSHAKE_TIMEOUT * 2);

      expect(get(client.isConnected)).toBe(true);
      expect(lastSocket().closeCalled).toBe(false);
    });

    it('should not report a timeout for an attempt that closed just before the deadline', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.HANDSHAKE_TIMEOUT - 1);

      lastSocket().fail();
      await vi.advanceTimersByTimeAsync(1);

      expect(get(client.lastError)).toContain('connection error');
    });

    it('should ignore callbacks from a socket superseded by a manual connect', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      client.connect();
      const stale = lastSocket();
      stale.fail();

      client.connect();
      const current = lastSocket();
      current.open();
      stale.drop();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY * 2);

      expect(get(client.isConnected)).toBe(true);
      expect(FakeWebSocket.instances).toHaveLength(2);
    });
  });

  describe('takeover', () => {
    it('should run the takeover callback and not reconnect when the server then closes', async () => {
      vi.useFakeTimers();
      const client = useWalletProxyClient();
      const takeover = vi.fn();
      client.onTakeOver(takeover);
      client.connect();
      lastSocket().open();

      lastSocket().receive({ type: 'reconnected' });
      lastSocket().drop();
      await vi.advanceTimersByTimeAsync(CLIENT_CONFIG.RETRY_DELAY * 2);

      expect(takeover).toHaveBeenCalledTimes(1);
      expect(FakeWebSocket.instances).toHaveLength(1);
      expect(get(client.state).phase).toBe(BridgeConnectionPhase.takenOver);
    });
  });
});
