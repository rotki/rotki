import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { BlockchainRefreshButtonBehaviour } from '@/modules/settings/types/frontend-settings';

const mocks = vi.hoisted(() => {
  const calls: string[] = [];
  return {
    calls,
    fetchBankBalances: vi.fn<(ignoreCache?: boolean) => Promise<void>>(),
    fetchConnectedExchangeBalances: vi.fn<(ignoreCache?: boolean) => Promise<void>>(),
    refreshBankConnections: vi.fn<() => Promise<void>>(),
    refreshBlockchainBalances: vi.fn<(...args: unknown[]) => Promise<void>>(),
  };
});

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: (): Record<string, unknown> => ({ detectAllTokens: vi.fn() }),
}));

vi.mock('@/modules/balances/exchanges/use-exchanges', () => ({
  useExchanges: (): Record<string, unknown> => ({
    fetchConnectedExchangeBalances: mocks.fetchConnectedExchangeBalances,
    fetchSelectedExchangeBalances: vi.fn(),
  }),
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

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): unknown => ref(BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES),
}));

describe('useBalanceRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.calls.length = 0;
    mocks.refreshBankConnections.mockImplementation(async () => {
      mocks.calls.push('connections');
    });
    mocks.fetchBankBalances.mockImplementation(async () => {
      mocks.calls.push('balances');
    });
  });

  it('should refresh blockchain balances for the blockchain card', async () => {
    await useBalanceRefresh().refreshBalance('blockchain');
    expect(mocks.refreshBlockchainBalances).toHaveBeenCalledOnce();
  });

  it('should query exchange balances ignoring the cache for the exchange card', async () => {
    await useBalanceRefresh().refreshBalance('exchange');
    expect(mocks.fetchConnectedExchangeBalances).toHaveBeenCalledWith(true);
  });

  it('should query bank balances ignoring the cache for the bank card', async () => {
    await useBalanceRefresh().refreshBalance('bank');
    expect(mocks.fetchBankBalances).toHaveBeenCalledWith(true);
  });

  it('should list the bank connections before querying bank balances, so an empty store can recover', async () => {
    await useBalanceRefresh().refreshBalance('bank');
    expect(mocks.calls).toEqual(['connections', 'balances']);
  });
});
