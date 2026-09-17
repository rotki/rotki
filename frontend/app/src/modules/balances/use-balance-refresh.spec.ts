import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref, type Ref } from 'vue';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { BlockchainRefreshButtonBehaviour } from '@/modules/settings/types/frontend-settings';

const mocks = vi.hoisted(() => {
  const calls: string[] = [];
  return {
    behaviour: { value: '' },
    calls,
    detectAllTokens: vi.fn<(chains?: string | string[]) => Promise<void>>(),
    fetchBankBalances: vi.fn<(ignoreCache?: boolean) => Promise<void>>(),
    fetchConnectedExchangeBalances: vi.fn<(ignoreCache?: boolean) => Promise<void>>(),
    fetchManualBalances: vi.fn<(userInitiated?: boolean) => Promise<void>>(),
    refreshBankConnections: vi.fn<() => Promise<void>>(),
    refreshBlockchainBalances: vi.fn<(...args: unknown[]) => Promise<void>>(),
    refreshPrices: vi.fn<(ignoreCache?: boolean) => Promise<void>>(),
  };
});

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: (): Record<string, unknown> => ({ detectAllTokens: mocks.detectAllTokens }),
}));

vi.mock('@/modules/balances/exchanges/use-exchanges', () => ({
  useExchanges: (): Record<string, unknown> => ({
    fetchConnectedExchangeBalances: mocks.fetchConnectedExchangeBalances,
    fetchSelectedExchangeBalances: vi.fn(),
  }),
}));

vi.mock('@/modules/balances/manual/use-manual-balances', () => ({
  useManualBalances: (): Record<string, unknown> => ({ fetchManualBalances: mocks.fetchManualBalances }),
}));

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: (): Record<string, unknown> => ({ refreshBlockchainBalances: mocks.refreshBlockchainBalances }),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({
    fetchBankBalances: mocks.fetchBankBalances,
    refreshBankConnections: mocks.refreshBankConnections,
  }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: (): Record<string, unknown> => ({ refreshPrices: mocks.refreshPrices }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    supportedChains: ref([{ id: 'eth' }, { id: 'btc' }]),
    supportsTransactions: (chain: string): boolean => chain === 'eth',
  }),
}));

vi.mock('@/modules/settings/use-setting', async () => {
  const { toRef } = await import('vue');
  return { useSetting: (): Readonly<Ref<string>> => toRef(() => mocks.behaviour.value) };
});

describe('useBalanceRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.calls.length = 0;
    mocks.behaviour.value = BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES;
    mocks.refreshBankConnections.mockImplementation(async () => {
      mocks.calls.push('connections');
    });
    mocks.fetchBankBalances.mockImplementation(async () => {
      mocks.calls.push('balances');
    });
  });

  describe('refreshAll', () => {
    it('should query every supported chain in user mode', async () => {
      await useBalanceRefresh().refreshAll();
      expect(mocks.refreshBlockchainBalances).toHaveBeenCalledExactlyOnceWith({ blockchain: ['eth', 'btc'] }, RefreshMode.USER);
    });

    it('should query exchange and bank balances ignoring the cache', async () => {
      await useBalanceRefresh().refreshAll();
      expect(mocks.fetchConnectedExchangeBalances).toHaveBeenCalledExactlyOnceWith(true);
      expect(mocks.fetchBankBalances).toHaveBeenCalledExactlyOnceWith(true);
    });

    it('should reload manual balances as a user request, so a recent load does not skip it', async () => {
      await useBalanceRefresh().refreshAll();
      expect(mocks.fetchManualBalances).toHaveBeenCalledExactlyOnceWith(true);
    });

    it('should list the bank connections before querying bank balances, so an empty store can recover', async () => {
      await useBalanceRefresh().refreshAll();
      expect(mocks.calls).toEqual(['connections', 'balances']);
    });

    it('should refresh prices ignoring the cache', async () => {
      await useBalanceRefresh().refreshAll();
      expect(mocks.refreshPrices).toHaveBeenCalledExactlyOnceWith(true);
    });

    it('should not redetect even when the user chose redetect for the refresh button', async () => {
      mocks.behaviour.value = BlockchainRefreshButtonBehaviour.REDETECT_TOKENS;
      await useBalanceRefresh().refreshAll();

      expect(mocks.detectAllTokens).not.toHaveBeenCalled();
      expect(mocks.refreshBlockchainBalances).toHaveBeenCalledExactlyOnceWith({ blockchain: ['eth', 'btc'] }, RefreshMode.USER);
    });
  });

  describe('redetectAndRefreshAll', () => {
    it('should redetect even when the user chose to only refresh', async () => {
      await useBalanceRefresh().redetectAndRefreshAll();

      expect(mocks.detectAllTokens).toHaveBeenCalledExactlyOnceWith(['eth']);
      expect(mocks.refreshBlockchainBalances).toHaveBeenCalledExactlyOnceWith({ blockchain: ['btc'] }, RefreshMode.USER);
    });
  });

  it('should not redetect when refreshing the blockchain source even when the user chose redetect', async () => {
    mocks.behaviour.value = BlockchainRefreshButtonBehaviour.REDETECT_TOKENS;
    await useBalanceRefresh().refreshSourceAndPrices('blockchain');

    expect(mocks.detectAllTokens).not.toHaveBeenCalled();
    expect(mocks.refreshBlockchainBalances).toHaveBeenCalledExactlyOnceWith({ blockchain: ['eth', 'btc'] }, RefreshMode.USER);
    expect(mocks.refreshPrices).toHaveBeenCalledExactlyOnceWith(true);
  });

  describe('handleBlockchainRefresh', () => {
    it('should detect on detection chains and query the rest when the user chose redetect', async () => {
      mocks.behaviour.value = BlockchainRefreshButtonBehaviour.REDETECT_TOKENS;
      await useBalanceRefresh().handleBlockchainRefresh();

      expect(mocks.detectAllTokens).toHaveBeenCalledExactlyOnceWith(['eth']);
      expect(mocks.refreshBlockchainBalances).toHaveBeenCalledExactlyOnceWith({ blockchain: ['btc'] }, RefreshMode.USER);
    });

    it('should redetect when forced even if the user chose to only refresh', async () => {
      await useBalanceRefresh().handleBlockchainRefresh(['eth'], true);

      expect(mocks.detectAllTokens).toHaveBeenCalledExactlyOnceWith(['eth']);
      expect(mocks.refreshBlockchainBalances).not.toHaveBeenCalled();
    });
  });

  it('should only refresh prices for the prices action', async () => {
    await useBalanceRefresh().refreshAllPrices();

    expect(mocks.refreshPrices).toHaveBeenCalledExactlyOnceWith(true);
    expect(mocks.refreshBlockchainBalances).not.toHaveBeenCalled();
  });
});
