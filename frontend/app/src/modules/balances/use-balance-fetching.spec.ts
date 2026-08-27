import { runSpecWith } from '@test/utils/mocks/native-task';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceFetching } from './use-balance-fetching';
import '@test/i18n';

const { refreshBlockchainBalances, detectDue, fetchAccounts, withDetection, skipReason, willDetect, queryBalancesAsync, snapshotDue, isSnapshotDue } = vi.hoisted(() => {
  // Whether a detection sweep is due this run. The real composable decides it from the cooldown
  // settings; here a test sets it directly and `withDetection` hands it to the pass.
  const detectDue = { value: false };
  // Whether the backend's snapshot schedule is due; `useSnapshotSchedule` is tested on its own.
  const snapshotDue = { value: true };
  return {
    detectDue,
    isSnapshotDue: vi.fn(async () => snapshotDue.value),
    snapshotDue,
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

vi.mock('@/modules/balances/use-snapshot-schedule', () => ({
  useSnapshotSchedule: (): { isSnapshotDue: typeof isSnapshotDue } => ({ isSnapshotDue }),
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

  describe('autoRefresh', () => {
    it('should perform auto refresh of balances and prices', async () => {
      const { autoRefresh } = useBalanceFetching();
      await expect(autoRefresh()).resolves.not.toThrow();
    });

    /**
     * 🔴 The periodic tick never asked a chain anything. `{ periodic: true }` went to
     * `refreshAccounts`, whose no-chain branch is a *cached* read — the DB, not the network — so
     * "Automatic balance refresh" only re-read what the backend had already written, and the
     * `periodic` refresh mode had no caller that could reach it.
     */
    it('should run a periodic refresh over every chain', async () => {
      refreshBlockchainBalances.mockClear();
      const { autoRefresh } = useBalanceFetching();

      await autoRefresh();

      expect(refreshBlockchainBalances).toHaveBeenCalledWith({}, 'periodic');
      // Accounts are re-read too, but as an accounts read — it no longer pretends to do more.
      expect(fetchAccounts).toHaveBeenCalledWith({ refreshEns: true });
    });
  });

  describe('refreshFromChain', () => {
    beforeEach(() => {
      refreshBlockchainBalances.mockClear();
      queryBalancesAsync.mockClear();
      withDetection.mockClear();
      detectDue.value = false;
      snapshotDue.value = true;
    });

    it('should refresh every chain, without detection, when none is due', async () => {
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(refreshBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(refreshBlockchainBalances).toHaveBeenCalledWith({}, 'background', { detect: false });
    });

    /**
     * ⭐ §3/§10. This used to split: fire detection for the EVM chains and separately refresh only
     * the non-EVM ones, because detection ended in its own balance read and refreshing an EVM chain
     * too would have queried it twice. Detection is now a stage inside each chain job that the
     * chain's own query follows, so it is one call for every chain either way.
     */
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

    it('should query all balances when the snapshot schedule is due', async () => {
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(queryBalancesAsync).toHaveBeenCalledOnce();
    });

    it('should query all balances when detecting too', async () => {
      detectDue.value = true;
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(queryBalancesAsync).toHaveBeenCalledOnce();
    });

    /** The backend saves on `requested_save_data or should_save_balances`; a refresh only asks. */
    it('should ask for a snapshot rather than force one', async () => {
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(queryBalancesAsync).toHaveBeenCalledWith({});
    });

    it('should not query all balances when the snapshot schedule is not due', async () => {
      snapshotDue.value = false;
      const { refreshFromChain } = useBalanceFetching();

      await refreshFromChain();

      expect(refreshBlockchainBalances).toHaveBeenCalledOnce();
      expect(queryBalancesAsync).not.toHaveBeenCalled();
    });

    it('should not ask for a snapshot when the chain refresh throws', async () => {
      refreshBlockchainBalances.mockRejectedValueOnce(new Error('chains failed'));
      const { refreshFromChain } = useBalanceFetching();

      await expect(refreshFromChain()).rejects.toThrow('chains failed');

      expect(queryBalancesAsync).not.toHaveBeenCalled();
    });

    /** Querying while chains were still repopulating is what wrote 0-value rows to net worth. */
    it('should query all balances only after every chain has settled', async () => {
      let settleChains: () => void = () => {};
      refreshBlockchainBalances.mockImplementationOnce(async () => new Promise<void>((resolve) => {
        settleChains = resolve;
      }));
      const { refreshFromChain } = useBalanceFetching();

      const refreshing = refreshFromChain();
      await flushPromises();

      expect(refreshBlockchainBalances).toHaveBeenCalledOnce();
      expect(queryBalancesAsync).not.toHaveBeenCalled();

      settleChains();
      await refreshing;

      expect(queryBalancesAsync).toHaveBeenCalledOnce();
    });
  });
});
