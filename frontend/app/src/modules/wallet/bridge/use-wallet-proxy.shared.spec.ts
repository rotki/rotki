import { createMock } from '@test/utils/create-mock';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWalletBridge } from '@/modules/shell/app/use-wallet-bridge';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('@/modules/shell/app/use-wallet-bridge', () => ({ useWalletBridge: vi.fn() }));

describe('modules/wallet/bridge/use-wallet-proxy sharing', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.mocked(useWalletBridge).mockReturnValue(createMock<ReturnType<typeof useWalletBridge>>({
      isProxyClientConnected: vi.fn(async () => false),
    }));
  });

  it('should hand every consumer the same instance', async () => {
    const { useWalletProxy } = await import('./use-wallet-proxy');

    const fromStore = withSetup(() => useWalletProxy()).result;
    const fromInjectedWallet = withSetup(() => useWalletProxy()).result;

    expect(fromInjectedWallet).toBe(fromStore);
  });

  it('should let one consumer stop a health check another consumer started', async () => {
    vi.useFakeTimers();
    const { useWalletProxy } = await import('./use-wallet-proxy');

    const starter = withSetup(() => useWalletProxy()).result;
    const stopper = withSetup(() => useWalletProxy()).result;

    const onDisconnect = vi.fn();
    starter.startConnectionHealthCheck(() => true, onDisconnect);
    // the interval lives on the shared instance, so the other handle owns it too
    stopper.stopConnectionHealthCheck();

    await vi.advanceTimersByTimeAsync(120_000);

    expect(onDisconnect).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
