import type { EvmChainInfo, SupportedChains } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { createCustomPinia } from '@test/utils/create-pinia';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { type RefreshMode, useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({}),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({
    updateBalances: vi.fn(),
  }),
}));

vi.mock('@/modules/balances/api/use-blockchain-balances-api', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    queryBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 1 }),
    refreshBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 4 }),
    queryXpubBalances: vi.fn().mockResolvedValue({ taskId: 3 }),
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    // Blockchain balances run native via runTaskResult (plainfp Result).
    runTaskResult: vi.fn().mockImplementation(async (taskFn: () => Promise<unknown>) => {
      await taskFn();
      const { ok } = await import('plainfp/result');
      return ok({
        perAccount: {},
        totals: {
          assets: {},
          liabilities: {},
        },
      });
    }),
  }),
}));

// The balance processing service takes its runner from the activity, so the stub passes one that
// resolves like the backend task would.
//
// `submitTask` and `supersedeTask` are separate stubs that both run the spec inline. The real
// difference between them (cancel, await the cancelled promise, resubmit) belongs to
// `useNativeTask` and is covered by its own spec; what this file owns is which of the two a given
// refresh mode routes to.
const { runTask } = vi.hoisted(() => ({ runTask: vi.fn() }));
const submitTask = vi.fn();
const supersedeTask = vi.fn();

vi.mock('@/modules/task-center/use-native-task', async () => {
  const { ok } = await import('plainfp/result');
  runTask.mockImplementation(async (taskFn: () => Promise<unknown>) => {
    await taskFn();
    return ok({ perAccount: {}, totals: { assets: {}, liabilities: {} } });
  });

  return {
    useNativeTask: vi.fn(() => ({
      reportProgress: vi.fn(),
      submitTask,
      supersedeTask,
    })),
  };
});

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return ({
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: (chain: string) => chain,
      getChainAccountType: (chain: Blockchain) => chain === Blockchain.BTC ? 'bitcoin' : 'evm',
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      getChainName: (chain: Blockchain) => chain === Blockchain.BTC ? 'Bitcoin' : 'Ethereum',
      getNativeAsset: (chain: Blockchain) => chain,
      supportedChains: computed<SupportedChains>(() => [
        {
          evmChainName: 'ethereum',
          id: Blockchain.ETH,
          image: '',
          name: 'Ethereum',
          nativeToken: 'ETH',
          type: 'evm',
        } satisfies EvmChainInfo,
        {
          id: Blockchain.BTC,
          image: '',
          name: 'Bitcoin',
          type: 'bitcoin',
        },
      ]),
    }),
  });
});

describe('useBlockchainBalances', () => {
  let api: ReturnType<typeof useBlockchainBalancesApi>;
  let blockchainBalances: ReturnType<typeof useBlockchainBalances>;

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    api = useBlockchainBalancesApi();
    blockchainBalances = useBlockchainBalances();
    vi.clearAllMocks();
    submitTask.mockImplementation(runSpecWith(runTask));
    supersedeTask.mockImplementation(runSpecWith(runTask));
  });

  describe('refreshBlockchainBalances', () => {
    beforeEach(() => {
      // refresh only calls the api when the chain has an account (see executeBalanceQuery);
      // add one per test so these cases don't rely on state left by a sibling test.
      const { updateAccounts } = useBlockchainAccountsStore();
      updateAccounts(Blockchain.ETH, [
        createAccount(
          { address: '0x49ff149D649769033d43783E7456F626862CD160', label: null, tags: null },
          { chain: Blockchain.ETH, nativeAsset: 'ETH' },
        ),
      ]);
    });

    it('should refresh particular blockchain - default', () => {
      const call = async (mode: RefreshMode = 'periodic'): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
          },
          mode,
        );
      };

      const assert = (times = 1): void => {
        expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(times);
        expect(api.refreshBlockchainBalances).toHaveBeenCalledWith({
          addresses: undefined,
          blockchain: Blockchain.ETH,
          isXpub: false,
        });
      };

      startPromise(call());
      assert();
    });

    it('should ignore periodic balance refresh, when there are other task running', async () => {
      const call = async (mode: RefreshMode = 'periodic'): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
          },
          mode,
        );
      };

      const assert = (times = 1): void => {
        expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(times);
        expect(api.refreshBlockchainBalances).toHaveBeenCalledWith({
          addresses: undefined,
          blockchain: Blockchain.ETH,
          isXpub: false,
        });
      };

      const refreshState = useBalanceRefreshState();
      const loading = refreshState.useIsRefreshing(Blockchain.ETH);

      startPromise(call());
      assert(1);

      startPromise(call());
      assert(1);

      await until(loading).toBe(false);
      assert(1);
    });

    /**
     * ⭐ §7. A user pressing refresh on a busy chain supersedes the run in flight instead of
     * joining it, so they get a fresh query with their own parameters rather than the background
     * run's. This replaced an `until(() => isChainRefreshing(chain)).toBe(false)` poll that reached
     * a similar outcome by waiting out work the user had already superseded.
     *
     * The cancel/await/resubmit mechanics live in `useNativeTask` and are covered there; the
     * routing decision is what belongs here.
     */
    it('should supersede a running refresh when the user asks for one', async () => {
      const call = async (mode: RefreshMode): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, mode);
      };

      await call('periodic');
      expect(submitTask).toHaveBeenCalledTimes(1);
      expect(supersedeTask).not.toHaveBeenCalled();

      await call('user');
      expect(supersedeTask).toHaveBeenCalledTimes(1);
      // Not joined onto the background run: the user's press genuinely re-queried.
      expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(2);
    });

    it('should join, not supersede, a background refresh', async () => {
      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background');

      expect(submitTask).toHaveBeenCalledTimes(1);
      expect(supersedeTask).not.toHaveBeenCalled();
    });

    it('should refresh balances with isXpub flag set to true', async () => {
      const { updateAccounts } = useBlockchainAccountsStore();

      // Add a BTC account first
      updateAccounts(Blockchain.BTC, [
        createAccount(
          { address: 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz', label: null, tags: null },
          { chain: Blockchain.BTC, nativeAsset: 'BTC' },
        ),
      ]);

      await blockchainBalances.refreshBlockchainBalances({
        blockchain: Blockchain.BTC,
        isXpub: true,
      });

      expect(api.queryXpubBalances).toHaveBeenCalledWith({
        addresses: undefined,
        blockchain: Blockchain.BTC,
        isXpub: true,
      });
    });
  });
});
