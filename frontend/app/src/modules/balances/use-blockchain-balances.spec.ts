import type { EvmChainInfo, SupportedChains } from '@/modules/api/types/chains';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { createTestBalance, createTestBalanceResponse } from '@test/utils/create-data';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { Section } from '@/modules/common/status';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { createAccount } from '@/utils/blockchain/accounts/create';

vi.mock('@/store/settings/general', async () => {
  const { ref } = await import('vue');
  const { Module } = await import('@/modules/common/modules');
  return ({
    useGeneralSettingsStore: vi.fn().mockReturnValue({
      activeModules: ref([Module.LOOPRING]),
    }),
  });
});

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({}),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({
    updateBalances: vi.fn(),
  }),
}));

vi.mock('@/composables/assets/common', () => ({
  useResolveAssetIdentifier: vi.fn(() => (asset: string): string => asset),
}));

vi.mock('@/composables/api/balances/blockchain', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    queryBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 1 }),
    refreshBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 4 }),
    queryLoopringBalances: vi.fn().mockResolvedValue({ taskId: 2 }),
    queryXpubBalances: vi.fn().mockResolvedValue({ taskId: 3 }),
  }),
}));

vi.mock('@/modules/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: vi.fn().mockImplementation(async (taskFn: () => Promise<unknown>, options: { type: number }) => {
      await taskFn();
      const { TaskType } = await import('@/modules/tasks/task-type');
      if (options.type === TaskType.L2_LOOPRING) {
        return {
          success: true,
          result: {
            '0x1234567890abcdef1234567890abcdef12345678': {
              ETH: createTestBalanceResponse(1.5, 3000),
              LRC: createTestBalanceResponse(100, 50),
            },
          },
        };
      }
      return {
        success: true,
        result: {
          perAccount: {},
          totals: {
            assets: {},
            liabilities: {},
          },
        },
      };
    }),
  }),
}));

vi.mock('@/composables/info/chains', async () => {
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

vi.mock('@/modules/balances/use-balance-queue', () => ({
  useBalanceQueue: vi.fn().mockReturnValue({
    queueBalanceQueries: vi.fn().mockImplementation(async (chains, fn) => {
      // Execute the functions immediately for testing
      for (const chain of chains) {
        await fn(chain);
      }
    }),
  }),
}));

describe('useBlockchainBalances', () => {
  setActivePinia(createPinia());
  let api: ReturnType<typeof useBlockchainBalancesApi> = useBlockchainBalancesApi();
  let blockchainBalances: ReturnType<typeof useBlockchainBalances> = useBlockchainBalances();

  beforeEach(() => {
    api = useBlockchainBalancesApi();
    blockchainBalances = useBlockchainBalances();
    vi.clearAllMocks();
  });

  describe('fetchBlockchainBalances', () => {
    it('should fetch all supported blockchains', async () => {
      const { updateAccounts } = useBlockchainAccountsStore();
      // won't call if no account
      await blockchainBalances.fetchBlockchainBalances();

      expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(0);

      // call if there's account
      updateAccounts(Blockchain.ETH, [
        createAccount(
          { address: '0x49ff149D649769033d43783E7456F626862CD160', label: null, tags: null },
          { chain: Blockchain.ETH, nativeAsset: 'ETH' },
        ),
      ]);

      await blockchainBalances.fetchBlockchainBalances();

      expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(api.queryBlockchainBalances).toHaveBeenCalledWith({
        addresses: undefined,
        blockchain: 'eth',
        isXpub: false,
      }, undefined);
    });
  });

  describe('refreshBlockchainBalances', () => {
    it('should refresh particular blockchain - default', () => {
      const call = async (periodic = true): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
          },
          periodic,
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
      const call = async (periodic = true): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
          },
          periodic,
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

      const { useIsLoading } = useStatusStore();
      const loading = useIsLoading(Section.BLOCKCHAIN, Blockchain.ETH);

      startPromise(call());
      assert(1);

      startPromise(call());
      assert(1);

      await until(loading).toBe(false);
      assert(1);
    });

    it('should queue manual balance refresh, after other task is done', async () => {
      const call = async (periodic = true): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
          },
          periodic,
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

      const { useIsLoading } = useStatusStore();
      const loading = useIsLoading(Section.BLOCKCHAIN, Blockchain.ETH);

      startPromise(call());
      assert(1);

      startPromise(call(false));
      assert(1);

      await until(loading).toBe(false);
      await nextTick();
      assert(2);
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

  describe('fetchLoopringBalances', () => {
    it('should fetch loopring balances when module is active', async () => {
      const { updateBalances } = useBalancesStore();
      await blockchainBalances.fetchLoopringBalances(false);

      expect(api.queryLoopringBalances).toHaveBeenCalledTimes(1);
      expect(updateBalances).toHaveBeenCalledWith('loopring', {
        perAccount: {
          loopring: {
            '0x1234567890abcdef1234567890abcdef12345678': {
              assets: {
                ETH: {
                  address: createTestBalance(1.5, 3000),
                },
                LRC: {
                  address: createTestBalance(100, 50),
                },
              },
              liabilities: {},
            },
          },
        },
        totals: {
          assets: {
            ETH: {
              address: createTestBalance(1.5, 3000),
            },
            LRC: {
              address: createTestBalance(100, 50),
            },
          },
          liabilities: {},
        },
      });
    });

    it('should not fetch loopring balances when module is not active', async () => {
      const { activeModules } = storeToRefs(useGeneralSettingsStore());
      set(activeModules, []);

      await blockchainBalances.fetchLoopringBalances(false);

      expect(api.queryLoopringBalances).not.toHaveBeenCalled();
    });
  });
});
