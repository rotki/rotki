import { createMock } from '@test/utils/create-mock';
import { withSetup } from '@test/utils/with-setup';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { waitForCondition } from '@/modules/core/common/async/async-utilities';
import { useWalletBridge } from '@/modules/shell/app/use-wallet-bridge';
import { useWalletProxy } from './use-wallet-proxy';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('@/modules/shell/app/use-wallet-bridge', () => ({ useWalletBridge: vi.fn() }));
vi.mock('@/modules/core/common/async/async-utilities', () => ({ waitForCondition: vi.fn(async () => true) }));

type BridgeMethod = 'isProxyClientConnected' | 'isProxyClientReady' | 'isProxyHttpListening' | 'isProxyWebSocketListening' | 'openProxyPageInDefaultBrowser' | 'proxyStopServers';
let bridge: Record<BridgeMethod, Mock>;

function stubWalletBridge(value: unknown): void {
  Object.defineProperty(window, 'walletBridge', { configurable: true, value });
}

describe('modules/wallet/bridge/use-wallet-proxy', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    bridge = {
      isProxyClientConnected: vi.fn(async () => true),
      isProxyClientReady: vi.fn(async () => true),
      isProxyHttpListening: vi.fn(async () => true),
      isProxyWebSocketListening: vi.fn(async () => true),
      openProxyPageInDefaultBrowser: vi.fn(async () => {}),
      proxyStopServers: vi.fn(async () => {}),
    };
    vi.mocked(useWalletBridge).mockReturnValue(createMock<ReturnType<typeof useWalletBridge>>(bridge));
    stubWalletBridge({ enable: vi.fn(async () => {}), isEnabled: vi.fn(() => true) });
  });

  afterEach(() => {
    Reflect.deleteProperty(window, 'walletBridge');
    vi.useRealTimers();
  });

  describe('setupProxy', () => {
    it('should return early without opening the page when fully connected and ready', async () => {
      const { setupProxy } = withSetup(() => useWalletProxy()).result;
      await setupProxy();
      expect(bridge.openProxyPageInDefaultBrowser).not.toHaveBeenCalled();
    });

    it('should open the bridge page when fully connected but the client is not ready', async () => {
      bridge.isProxyClientReady.mockResolvedValue(false);
      const { setupProxy } = withSetup(() => useWalletProxy()).result;
      await setupProxy();
      expect(bridge.openProxyPageInDefaultBrowser).toHaveBeenCalledTimes(1);
    });

    it('should start the servers when the bridge is not fully connected', async () => {
      bridge.isProxyClientConnected.mockResolvedValue(false);
      const { setupProxy } = withSetup(() => useWalletProxy()).result;
      await setupProxy();

      expect(bridge.openProxyPageInDefaultBrowser).toHaveBeenCalled();
      expect(vi.mocked(waitForCondition)).toHaveBeenCalled();
    });

    it('should enable the wallet bridge when it is disabled', async () => {
      const enable = vi.fn(async () => {});
      stubWalletBridge({ enable, isEnabled: vi.fn(() => false) });
      const { setupProxy } = withSetup(() => useWalletProxy()).result;
      await setupProxy();
      expect(enable).toHaveBeenCalledTimes(1);
    });

    it('should reject when the wallet bridge is missing from the window', async () => {
      Reflect.deleteProperty(window, 'walletBridge');
      const { setupProxy } = withSetup(() => useWalletProxy()).result;
      await expect(setupProxy()).rejects.toThrow('Wallet bridge not available in window object');
    });
  });

  describe('disconnectProxy', () => {
    it('should stop the servers', async () => {
      const { disconnectProxy } = withSetup(() => useWalletProxy()).result;
      await disconnectProxy();
      expect(bridge.proxyStopServers).toHaveBeenCalledTimes(1);
    });

    it('should throw when stopping the servers fails', async () => {
      bridge.proxyStopServers.mockRejectedValue(new Error('nope'));
      const { disconnectProxy } = withSetup(() => useWalletProxy()).result;
      await expect(disconnectProxy()).rejects.toThrow('Failed to stop bridge servers: nope');
    });
  });

  describe('health check', () => {
    it('should call onDisconnect and stop when the client drops', async () => {
      vi.useFakeTimers();
      bridge.isProxyClientConnected.mockResolvedValue(false);
      const onDisconnect = vi.fn();
      const { startConnectionHealthCheck } = withSetup(() => useWalletProxy()).result;

      startConnectionHealthCheck(() => true, onDisconnect);
      await vi.advanceTimersByTimeAsync(5000);

      expect(onDisconnect).toHaveBeenCalledTimes(1);
    });

    it('should not fire onDisconnect while the client stays connected', async () => {
      vi.useFakeTimers();
      bridge.isProxyClientConnected.mockResolvedValue(true);
      const onDisconnect = vi.fn();
      const { startConnectionHealthCheck, stopConnectionHealthCheck } = withSetup(() => useWalletProxy()).result;

      startConnectionHealthCheck(() => true, onDisconnect);
      await vi.advanceTimersByTimeAsync(5000);
      stopConnectionHealthCheck();

      expect(onDisconnect).not.toHaveBeenCalled();
    });

    it('should stop the interval so no further checks run', async () => {
      vi.useFakeTimers();
      const onDisconnect = vi.fn();
      const { startConnectionHealthCheck, stopConnectionHealthCheck } = withSetup(() => useWalletProxy()).result;

      startConnectionHealthCheck(() => true, onDisconnect);
      stopConnectionHealthCheck();
      bridge.isProxyClientConnected.mockClear();
      await vi.advanceTimersByTimeAsync(15000);

      expect(bridge.isProxyClientConnected).not.toHaveBeenCalled();
    });
  });
});
