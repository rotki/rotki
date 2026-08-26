import { runSpecWith } from '@test/utils/mocks/native-task';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceFetching } from './use-balance-fetching';
import '@test/i18n';

const { refreshBlockchainBalances, detectDue, fetchAccounts, withDetection, skipReason, willDetect, queryBalancesAsync } = vi.hoisted(() => {
  // Whether a detection sweep is due this run. The real composable decides it from the cooldown
  // settings; here a test sets it directly and `withDetection` hands it to the pass.
  const detectDue = { value: false };
  return {
    detectDue,
    fetchAccounts: vi.fn().mockResolvedValue(undefined),
    queryBalancesAsync: vi.fn().mockResolvedValue({ taskId: 1 }),
    refreshBlockchainBalances: vi.fn().mockResolvedValue(undefined),
    skipReason: vi.fn().mockReturnValue('auto-detect-tokens disabled'),
    willDetect: vi.fn(() => detectDue.value),
    withDetection: vi.fn(async (pass: (detect: boolean) => Promise<unknown>) => pass(detectDue.value)),
  };
});

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn().mockReturnValue({
    fetchBlockchainBalances: vi.fn().mockResolvedValue({}),
    refreshBlockchainBalances,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-auto-token-detection', () => ({
  useAutoTokenDetection: (): { skipReason: typeof skipReason; willDetect: typeof willDetect; withDetection: typeof withDetection } => ({
    skipReason,
    willDetect,
    withDetection,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      supportedChains: computed(() => [
        { id: Blockchain.ETH, type: 'evm', name: 'Ethereum', image: '', nativeToken: 'ETH' },
        { id: Blockchain.BTC, type: 'bitcoin', name: 'Bitcoin', image: '', nativeToken: 'BTC' },
      ]),
      txEvmChains: computed(() => [
        { id: Blockchain.ETH, evmChainName: 'ethereum', type: 'evm', name: 'Ethereum', image: '', nativeToken: 'ETH' },
      ]),
    }),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifyError: vi.fn(),
  }),
  getErrorMessage: vi.fn(),
}));

// The activity's task runner, handed to `run` by the stubbed `submitTask` below.
const { runTask } = vi.hoisted(() => ({ runTask: vi.fn() }));

vi.mock('@/modules/task-center/use-native-task', async () => {
  const { ok } = await import('plainfp/result');
  runTask.mockImplementation(async (taskFn: () => Promise<unknown>): Promise<unknown> => {
    await taskFn();
    return ok({});
  });

  return {
    useNativeTask: vi.fn().mockReturnValue({
      statusOf: vi.fn().mockReturnValue({ active: false, everCompleted: false, pending: false, running: false }),
      // Run the submitted spec inline so `queryBalancesAsync` is actually reached.
      submitTask: vi.fn(runSpecWith(runTask)),
    }),
  };
});

vi.mock('@/modules/balances/api/use-balances-api', () => ({
  useBalancesApi: vi.fn().mockReturnValue({
    queryBalancesAsync,
  }),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    fetchExchangeRates: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/balances/manual/use-manual-balances', () => ({
  useManualBalances: vi.fn().mockReturnValue({
    fetchManualBalances: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn().mockReturnValue({
    fetchAccounts,
  }),
}));

vi.mock('@/modules/balances/exchanges/use-exchanges', () => ({
  useExchanges: vi.fn().mockReturnValue({
    fetchConnectedExchangeBalances: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: vi.fn().mockReturnValue({
    fetchNetValue: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn().mockReturnValue({
    refreshPrices: vi.fn().mockResolvedValue({}),
  }),
}));

describe('useBalanceFetching', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('fetchBalances', () => {
    it('should handle balance fetching', async () => {
      const { fetchBalances } = useBalanceFetching();
      await expect(fetchBalances()).resolves.not.toThrow();
    });
  });

  describe('fetch', () => {
    it('should coordinate fetching of all balance types', async () => {
      const { fetch } = useBalanceFetching();
      await expect(fetch()).resolves.not.toThrow();
    });
  });

  describe('autoRefresh', () => {
    it('should query every chain in periodic mode, rather than re-reading the cache', async () => {
      refreshBlockchainBalances.mockClear();
      const { autoRefresh } = useBalanceFetching();

      await autoRefresh();

      expect(refreshBlockchainBalances).toHaveBeenCalledWith({}, 'periodic');
      expect(fetchAccounts).toHaveBeenCalledWith({ refreshEns: true });
    });
  });

  describe('refreshFromChain', () => {
    beforeEach(() => {
      refreshBlockchainBalances.mockClear();
      queryBalancesAsync.mockClear();
      withDetection.mockClear();
      detectDue.value = false;
    });

    it('should refresh every chain, without detection, when none is due', async () => {
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(refreshBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(refreshBlockchainBalances).toHaveBeenCalledWith({}, 'background', { detect: false });
    });

    it('should refresh every chain with detection when one is due', async () => {
      detectDue.value = true;
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(refreshBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(refreshBlockchainBalances).toHaveBeenCalledWith({}, 'background', { detect: true });
      // No chain list: the old branch narrowed to non-EVM chains here.
      expect(refreshBlockchainBalances).not.toHaveBeenCalledWith(
        expect.objectContaining({ blockchain: expect.anything() }),
        expect.anything(),
        expect.anything(),
      );
    });

    /**
     * Replaces "should query all balances only after the chain refresh completes", which pinned
     * an ordering that only mattered because the refresh asked for a snapshot at all.
     *
     * `GET /balances` persists on the backend's own schedule, so ending a refresh with it meant
     * requesting a snapshot while the per-chain queries were still clearing and repopulating
     * chains — the 0-value row. Nothing is lost by not asking: the backend takes automatic
     * snapshots itself (`_maybe_update_snapshot_balances`), and explicit ones go through
     * `forceSave`, which calls `fetchBalances` directly with `saveData: true`.
     */
    it('should not query all balances', async () => {
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(refreshBlockchainBalances).toHaveBeenCalledOnce();
      expect(queryBalancesAsync).not.toHaveBeenCalled();
    });

    it('should not query all balances when detecting either', async () => {
      detectDue.value = true;
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(queryBalancesAsync).not.toHaveBeenCalled();
    });
  });
});
