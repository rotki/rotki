import type { EffectScope } from 'vue';
import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import { createMock } from '@test/utils/create-mock';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeWalletActions } from '@/modules/wallet/send/use-trade-wallet-actions';

const connected = ref<boolean>(false);
const connectWallet = vi.fn<() => Promise<void>>();
const disconnectWallet = vi.fn<() => Promise<void>>();
const sendTransaction = vi.fn<() => Promise<string>>();
const handleProviderSelection = vi.fn<
  (provider: unknown, onError: (message: string) => void) => Promise<void>
>();

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn(() => ({
    connect: connectWallet,
    connected,
    disconnect: disconnectWallet,
    sendTransaction,
  })),
}));

vi.mock('@/modules/wallet/providers/use-provider-selection', () => ({
  useProviderSelection: vi.fn(() => ({ handleProviderSelection })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

const PARAMS = {
  amount: '1',
  assetIdentifier: 'ETH',
  chain: 'ethereum',
  native: true,
  to: '0x9531C059098e3d194fF87FebB587aB07B30B1306',
};

describe('useTradeWalletActions', () => {
  let scope: EffectScope;

  function create(): ReturnType<typeof useTradeWalletActions> {
    scope = effectScope();
    const result = scope.run(() => useTradeWalletActions());
    assert(result);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(connected, false);
    connectWallet.mockResolvedValue();
    disconnectWallet.mockResolvedValue();
    sendTransaction.mockResolvedValue('0xhash');
  });

  afterEach(() => {
    scope.stop();
  });

  it('should report a failed connection', async () => {
    connectWallet.mockRejectedValue(new Error('no provider found'));
    const { connect, errorMessage } = create();

    await connect();

    expect(get(errorMessage)).toBe('no provider found');
  });

  it('should report a failed disconnection', async () => {
    disconnectWallet.mockRejectedValue(new Error('still busy'));
    const { disconnect, errorMessage } = create();

    await disconnect();

    expect(get(errorMessage)).toBe('still busy');
  });

  it('should clear a previous error on the next attempt', async () => {
    connectWallet.mockRejectedValueOnce(new Error('no provider found'));
    const { connect, errorMessage } = create();
    await connect();
    expect(get(errorMessage)).toBe('no provider found');

    await connect();

    expect(get(errorMessage)).toBe('');
  });

  it('should connect when disconnected and disconnect when connected', async () => {
    const { toggleConnection } = create();

    await toggleConnection();
    expect(connectWallet).toHaveBeenCalledOnce();
    expect(disconnectWallet).not.toHaveBeenCalled();

    set(connected, true);
    await toggleConnection();

    expect(disconnectWallet).toHaveBeenCalledOnce();
  });

  it('should report a sent transaction so the form can be cleared', async () => {
    const { errorMessage, send } = create();

    const sent = await send(PARAMS);

    expect(sent).toBe(true);
    expect(sendTransaction).toHaveBeenCalledWith(PARAMS);
    expect(get(errorMessage)).toBe('');
  });

  it('should not report a failed transaction as sent', async () => {
    sendTransaction.mockRejectedValue(new Error('insufficient funds'));
    const { errorMessage, send } = create();

    const sent = await send(PARAMS);

    expect(sent).toBe(false);
    expect(get(errorMessage)).toBe('insufficient funds');
  });

  it('should name a user rejection rather than call it a wallet error', async () => {
    sendTransaction.mockRejectedValue(new Error('User rejected the request.'));
    const { errorMessage, send } = create();

    await send(PARAMS);

    expect(get(errorMessage)).toBe('trade.errors.rejected');
  });

  it('should surface a provider selection failure', async () => {
    handleProviderSelection.mockImplementation(async (_provider, onError) => {
      onError('that provider is unavailable');
    });
    const { errorMessage, selectProvider } = create();

    await selectProvider(createMock<EnhancedProviderDetail>());

    expect(get(errorMessage)).toBe('that provider is unavailable');
  });

  it('should clear the error on request', async () => {
    connectWallet.mockRejectedValue(new Error('no provider found'));
    const { clearError, connect, errorMessage } = create();
    await connect();

    clearError();

    expect(get(errorMessage)).toBe('');
  });
});
