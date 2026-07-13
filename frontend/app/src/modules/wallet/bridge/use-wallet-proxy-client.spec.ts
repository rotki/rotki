import type { WalletBridgeRequest, WalletBridgeResponse } from '@shared/wallet-bridge-types';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBridgeMessageHandlers } from '@/modules/wallet/bridge/use-bridge-message-handlers';
import { useWalletProxyClient } from './use-wallet-proxy-client';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('@/modules/wallet/bridge/use-bridge-message-handlers', () => ({
  useBridgeMessageHandlers: vi.fn(),
}));

let handleRequest: (message: WalletBridgeRequest) => Promise<WalletBridgeResponse>;

class FakeWebSocket {
  static readonly OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
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
    this.readyState = 3;
  }

  // test helpers
  open(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.({});
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

  it('should connect and flip isConnected on open', async () => {
    const client = useWalletProxyClient();
    await client.connect();
    expect(get(client.isConnecting)).toBe(true);

    lastSocket().open();
    expect(get(client.isConnected)).toBe(true);
    expect(get(client.isConnecting)).toBe(false);
    expect(lastSocket().url).toContain('/wallet-bridge');
  });

  it('should dispatch a request and send back the handler response', async () => {
    const client = useWalletProxyClient();
    await client.connect();
    lastSocket().open();

    lastSocket().receive({ id: 1, jsonrpc: '2.0', method: 'eth_chainId' });
    await flushPromises();

    expect(handleRequest).toHaveBeenCalledWith(expect.objectContaining({ method: 'eth_chainId' }));
    expect(lastSocket().sent).toContainEqual(JSON.stringify({ id: 1, jsonrpc: '2.0', result: '0x1' }));
  });

  it('should prevent reconnection and run the takeover callback on a reconnected notification', async () => {
    const client = useWalletProxyClient();
    const takeover = vi.fn();
    client.onTakeOver(takeover);
    await client.connect();
    lastSocket().open();

    lastSocket().receive({ type: 'reconnected' });
    expect(takeover).toHaveBeenCalledTimes(1);
  });

  it('should close the tab on a close_tab notification', async () => {
    const closeSpy = vi.spyOn(window, 'close').mockImplementation(() => {});
    const client = useWalletProxyClient();
    await client.connect();
    lastSocket().open();

    lastSocket().receive({ type: 'close_tab' });
    expect(closeSpy).toHaveBeenCalledTimes(1);
  });

  it('should not schedule a reconnect after an intentional disconnect', async () => {
    vi.useFakeTimers();
    const client = useWalletProxyClient();
    await client.connect();
    const socket = lastSocket();
    socket.open();

    client.disconnect();
    expect(get(client.isConnected)).toBe(false);

    // simulate the socket firing onclose after close()
    socket.onclose?.({});
    await vi.advanceTimersByTimeAsync(1000);
    // no new socket created by a retry
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('should schedule a reconnect after an unexpected close', async () => {
    vi.useFakeTimers();
    const client = useWalletProxyClient();
    await client.connect();
    const socket = lastSocket();
    socket.open();

    socket.onclose?.({}); // unexpected close (not intentional)
    await vi.advanceTimersByTimeAsync(600);

    expect(FakeWebSocket.instances.length).toBeGreaterThan(1);
  });

  it('should record the error message on socket error', async () => {
    vi.useFakeTimers();
    const client = useWalletProxyClient();
    await client.connect();
    const socket = lastSocket();

    socket.onerror?.({});
    expect(get(client.lastError)).toContain('WebSocket connection error');
  });
});
