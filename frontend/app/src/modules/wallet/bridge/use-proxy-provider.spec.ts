import type { RpcRequest } from '@/types';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useProxyProvider } from '@/modules/wallet/bridge/use-proxy-provider';

interface MockWalletBridge {
  isEnabled: ReturnType<typeof vi.fn<() => boolean>>;
  isConnected: ReturnType<typeof vi.fn<() => boolean>>;
  disable: ReturnType<typeof vi.fn<() => Promise<void>>>;
  request: ReturnType<typeof vi.fn<(req: RpcRequest) => Promise<unknown>>>;
  addEventListener: ReturnType<typeof vi.fn<(name: string, cb: (data: unknown) => void) => void>>;
  removeEventListener: ReturnType<typeof vi.fn<(name: string) => void>>;
}

function createMockBridge(): MockWalletBridge {
  return {
    addEventListener: vi.fn(),
    disable: vi.fn().mockResolvedValue(undefined),
    isConnected: vi.fn().mockReturnValue(true),
    isEnabled: vi.fn().mockReturnValue(true),
    removeEventListener: vi.fn(),
    request: vi.fn().mockResolvedValue('result'),
  };
}

function installBridge(bridge: MockWalletBridge | undefined): void {
  // Type-narrowed assignment: the global `Window.walletBridge` is `WalletBridgeApi | undefined`,
  // and the structural shape of MockWalletBridge satisfies the subset our SUT calls.
  Object.assign(window, { walletBridge: bridge });
}

describe('useProxyProvider', () => {
  let bridge: MockWalletBridge;

  beforeEach(() => {
    bridge = createMockBridge();
    installBridge(bridge);
  });

  afterEach(() => {
    installBridge(undefined);
  });

  it('should return undefined when no wallet bridge is available', () => {
    installBridge(undefined);
    expect(useProxyProvider()).toBeUndefined();
  });

  it('should expose isRotkiBridge true and reflect bridge connection state', () => {
    const provider = useProxyProvider()!;
    expect(provider).toBeDefined();
    expect(provider.isRotkiBridge).toBe(true);
    expect(provider.connected).toBe(true);

    bridge.isConnected.mockReturnValue(false);
    expect(provider.connected).toBe(false);
  });

  it('should forward requests to the bridge', async () => {
    const provider = useProxyProvider()!;
    const request: RpcRequest = { method: 'eth_accounts' };
    const result = await provider.request(request);

    expect(bridge.request).toHaveBeenCalledWith(request);
    expect(result).toBe('result');
  });

  it('should call bridge.disable() on disconnect', async () => {
    const provider = useProxyProvider()!;
    await provider.disconnect!();
    expect(bridge.disable).toHaveBeenCalledOnce();
  });

  it('should register a single bridge listener per event type and forward emissions', () => {
    const provider = useProxyProvider()!;
    const handlerA = vi.fn();
    const handlerB = vi.fn();

    provider.on!('accountsChanged', handlerA);
    provider.on!('accountsChanged', handlerB);

    expect(bridge.addEventListener).toHaveBeenCalledTimes(1);
    expect(bridge.addEventListener).toHaveBeenCalledWith('accountsChanged', expect.any(Function));

    const forward = bridge.addEventListener.mock.calls[0][1];
    forward(['0xabc']);

    expect(handlerA).toHaveBeenCalledWith(['0xabc']);
    expect(handlerB).toHaveBeenCalledWith(['0xabc']);
  });

  it('should invoke disconnect listeners without arguments when bridge emits without data', () => {
    const provider = useProxyProvider()!;
    const handler = vi.fn();
    provider.on!('disconnect', handler);

    const forward = bridge.addEventListener.mock.calls[0][1];
    forward(undefined);
    expect(handler).toHaveBeenCalledWith();
  });

  it('should swallow errors from individual listeners so siblings still run', () => {
    const provider = useProxyProvider()!;
    const failing = vi.fn().mockImplementation(() => {
      throw new Error('listener failed');
    });
    const succeeding = vi.fn();

    provider.on!('accountsChanged', failing);
    provider.on!('accountsChanged', succeeding);

    const forward = bridge.addEventListener.mock.calls[0][1];
    expect(() => forward(['0x1'])).not.toThrow();
    expect(succeeding).toHaveBeenCalledWith(['0x1']);
  });

  it('should remove a listener and detach the bridge forwarder when none remain', () => {
    const provider = useProxyProvider()!;
    const handler = vi.fn();

    provider.on!('accountsChanged', handler);
    provider.removeListener!('accountsChanged', handler);

    expect(bridge.removeEventListener).toHaveBeenCalledWith('accountsChanged');

    const forward = bridge.addEventListener.mock.calls[0][1];
    forward(['0x1']);
    expect(handler).not.toHaveBeenCalled();
  });

  it('should keep the bridge forwarder when other listeners remain after removal', () => {
    const provider = useProxyProvider()!;
    const keep = vi.fn();
    const remove = vi.fn();

    provider.on!('accountsChanged', keep);
    provider.on!('accountsChanged', remove);
    provider.removeListener!('accountsChanged', remove);

    expect(bridge.removeEventListener).not.toHaveBeenCalled();

    const forward = bridge.addEventListener.mock.calls[0][1];
    forward(['0x1']);
    expect(keep).toHaveBeenCalledWith(['0x1']);
    expect(remove).not.toHaveBeenCalled();
  });

  it('should alias off() to removeListener()', () => {
    const provider = useProxyProvider()!;
    const handler = vi.fn();

    provider.on!('accountsChanged', handler);
    provider.off!('accountsChanged', handler);

    expect(bridge.removeEventListener).toHaveBeenCalledWith('accountsChanged');
  });
});
