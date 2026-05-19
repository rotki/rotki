import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useProviderSelection } from '@/modules/wallet/providers/use-provider-selection';

const selectProvider = vi.fn();
const connectToSelectedProvider = vi.fn();

vi.mock('@/modules/wallet/providers/use-unified-providers', () => ({
  useUnifiedProviders: vi.fn().mockImplementation(() => ({
    selectProvider,
  })),
}));

vi.mock('@/modules/wallet/bridge/use-injected-wallet', () => ({
  useInjectedWallet: vi.fn().mockImplementation(() => ({
    connectToSelectedProvider,
  })),
}));

function makeProvider(uuid = 'p1'): EnhancedProviderDetail {
  return {
    info: { icon: 'icon', name: 'Test', rdns: 'test.example', uuid },
    provider: { request: vi.fn() },
    source: 'eip6963',
  };
}

describe('useProviderSelection', () => {
  beforeEach(() => {
    selectProvider.mockReset().mockResolvedValue(undefined);
    connectToSelectedProvider.mockReset().mockResolvedValue(undefined);
  });

  it('should select the provider then connect to it', async () => {
    const { handleProviderSelection } = useProviderSelection();
    const onError = vi.fn();
    const provider = makeProvider('uuid-1');

    await handleProviderSelection(provider, onError);

    expect(selectProvider).toHaveBeenCalledWith('uuid-1');
    expect(connectToSelectedProvider).toHaveBeenCalledOnce();
    expect(onError).not.toHaveBeenCalled();
  });

  it('should report a user-rejection error with a specific message', async () => {
    selectProvider.mockRejectedValueOnce(new Error('User rejected the request'));
    const { handleProviderSelection } = useProviderSelection();
    const onError = vi.fn();

    await handleProviderSelection(makeProvider(), onError);

    expect(onError).toHaveBeenCalledWith('Wallet connection was rejected by user');
  });

  it('should report a timeout error with a specific message', async () => {
    connectToSelectedProvider.mockRejectedValueOnce(new Error('Request timeout after 30s'));
    const { handleProviderSelection } = useProviderSelection();
    const onError = vi.fn();

    await handleProviderSelection(makeProvider(), onError);

    expect(onError).toHaveBeenCalledWith('Connection request timed out. Please try again.');
  });

  it('should report a generic failure with the underlying error message', async () => {
    selectProvider.mockRejectedValueOnce(new Error('something exploded'));
    const { handleProviderSelection } = useProviderSelection();
    const onError = vi.fn();

    await handleProviderSelection(makeProvider(), onError);

    expect(onError).toHaveBeenCalledWith('Failed to connect wallet: something exploded');
  });

  it('should not call connectToSelectedProvider when selectProvider fails', async () => {
    selectProvider.mockRejectedValueOnce(new Error('boom'));
    const { handleProviderSelection } = useProviderSelection();
    await handleProviderSelection(makeProvider(), vi.fn());

    expect(connectToSelectedProvider).not.toHaveBeenCalled();
  });
});
