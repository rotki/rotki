import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountBalancesRefresh } from './use-account-balances-refresh';

const h = vi.hoisted(() => ({
  fetchAccounts: vi.fn(),
  handleBlockchainRefresh: vi.fn(),
  refreshBlockchainBalances: vi.fn(),
}));

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: vi.fn(() => ({
    handleBlockchainRefresh: h.handleBlockchainRefresh,
    refreshBlockchainBalances: h.refreshBlockchainBalances,
  })),
}));

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn(() => ({ fetchAccounts: h.fetchAccounts })),
}));

describe('useAccountBalancesRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch accounts then run the evm refresh for evm chains', async () => {
    const fetchData = vi.fn<() => Promise<void>>(async () => {});
    const { refreshClick } = useAccountBalancesRefresh({ chainIds: ['eth', 'optimism'], fetchData, isEvm: true });

    await refreshClick();

    expect(h.fetchAccounts).toHaveBeenCalledWith({ blockchain: ['eth', 'optimism'], refreshEns: true });
    expect(h.handleBlockchainRefresh).toHaveBeenCalledWith(['eth', 'optimism']);
    expect(h.refreshBlockchainBalances).not.toHaveBeenCalled();
    expect(fetchData).toHaveBeenCalledOnce();
  });

  it('should run the plain balance refresh for non-evm chains', async () => {
    const fetchData = vi.fn<() => Promise<void>>(async () => {});
    const { refreshClick } = useAccountBalancesRefresh({ chainIds: ['btc'], fetchData, isEvm: false });

    await refreshClick();

    expect(h.refreshBlockchainBalances).toHaveBeenCalledWith(['btc']);
    expect(h.handleBlockchainRefresh).not.toHaveBeenCalled();
    expect(fetchData).toHaveBeenCalledOnce();
  });

  it('should resolve reactive chain and evm inputs', async () => {
    const chainIds = ref<string[]>(['eth']);
    const isEvm = ref<boolean>(true);
    const fetchData = vi.fn<() => Promise<void>>(async () => {});
    const { refreshClick } = useAccountBalancesRefresh({ chainIds, fetchData, isEvm });

    set(isEvm, false);
    set(chainIds, ['btc']);
    await refreshClick();

    expect(h.fetchAccounts).toHaveBeenCalledWith({ blockchain: ['btc'], refreshEns: true });
    expect(h.refreshBlockchainBalances).toHaveBeenCalledWith(['btc']);
  });
});
