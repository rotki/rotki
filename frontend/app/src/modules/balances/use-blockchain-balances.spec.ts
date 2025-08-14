import type { EvmChainInfo, SupportedChains } from '@/types/api/chains';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { createTestBalance, createTestBalanceResponse } from '@test/utils/create-data';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { createAccount } from '@/utils/blockchain/accounts/create';

vi.mock('@/store/settings/general', async () => {
  const { ref } = await import('vue');
  const { Module } = await import('@/types/modules');
  return ({
    useGeneralSettingsStore: vi.fn().mockReturnValue({
      activeModules: ref([Module.LOOPRING]),
    }),
  });
});

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({
    updateBalances: vi.fn(),
  }),
}));

vi.mock('@/composables/assets/retrieval', async () => {
  const { ref } = await import('vue');
  return ({
    useAssetInfoRetrieval: vi.fn().mockReturnValue({
      getAssociatedAssetIdentifier: vi.fn().mockReturnValue(ref()),
    }),
  });
});

vi.mock('@/composables/api/balances/blockchain', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    queryBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 1 }),
    queryLoopringBalances: vi.fn().mockResolvedValue({ taskId: 2 }),
  }),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockImplementation(async (taskId) => {
      if (taskId === 2) {
        // Loopring balances response
        return {
          meta: { title: '' },
          result: {
            '0x1234567890abcdef1234567890abcdef12345678': {
              ETH: createTestBalanceResponse(1.5, 3000),
              LRC: createTestBalanceResponse(100, 50),
            },
          },
        };
      }
      // Default blockchain balances response
      return {
        meta: { title: '' },
        result: {
          perAccount: {},
          totals: {
            assets: {},
            liabilities: {},
          },
        },
      };
    }),
    isTaskRunning: vi.fn(),
  }),
}));

vi.mock('@/composables/info/chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return ({
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: () => Blockchain.ETH,
      getChainAccountType: () => 'evm',
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      getChainName: () => 'Ethereum',
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
      ]),
    }),
  });
});

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
    it('all supported blockchains', async () => {
      const { updateAccounts } = useBlockchainAccountsStore();
      // won't call if no account
      await blockchainBalances.fetchBlockchainBalances();

      expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(0);
      expect(api.queryBlockchainBalances).not.toHaveBeenCalledWith(false, 'eth');

      // call if there's account
      updateAccounts(Blockchain.ETH, [
        createAccount(
          { address: '0x49ff149D649769033d43783E7456F626862CD160', label: null, tags: null },
          { chain: Blockchain.ETH, nativeAsset: 'ETH' },
        ),
      ]);

      await blockchainBalances.fetchBlockchainBalances();

      expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(api.queryBlockchainBalances).toHaveBeenCalledWith(false, 'eth', undefined);
    });

    describe('particular blockchain', () => {
      const call = async (periodic = true): Promise<void> => {
        await blockchainBalances.fetchBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
            ignoreCache: true,
          },
          periodic,
        );
      };

      const assert = (times = 1): void => {
        expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(times);
        expect(api.queryBlockchainBalances).toHaveBeenCalledWith(true, Blockchain.ETH, undefined);
      };

      const { isLoading } = useStatusStore();
      const loading = isLoading(Section.BLOCKCHAIN, Blockchain.ETH);

      it('default', () => {
        startPromise(call());
        assert();
      });

      it('ignore periodic balance refresh, when there are other task running', async () => {
        startPromise(call());
        assert(1);

        startPromise(call());
        assert(1);

        await until(loading).toBe(false);
        assert(1);
      });

      it('queue manual balance refresh, after other task is done', async () => {
        startPromise(call());
        assert(1);

        startPromise(call(false));
        assert(1);

        await until(loading).toBe(false);
        assert(2);
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
