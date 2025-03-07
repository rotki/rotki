import type { EvmChainInfo, SupportedChains } from '@/types/api/chains';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useBlockchainBalances } from '@/composables/blockchain/balances';
import { useBlockchainStore } from '@/store/blockchain';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { createAccount } from '@/utils/blockchain/accounts/create';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/blockchain/balances/eth', () => ({
  useEthBalancesStore: vi.fn().mockReturnValue({
    updatePrices: vi.fn(),
    update: vi.fn(),
  }),
}));

vi.mock('@/store/blockchain/balances/btc', () => ({
  useBtcBalancesStore: vi.fn().mockReturnValue({
    updatePrices: vi.fn(),
    update: vi.fn(),
  }),
}));

vi.mock('@/store/blockchain/balances/chains', () => ({
  useChainBalancesStore: vi.fn().mockReturnValue({
    updatePrices: vi.fn(),
    update: vi.fn(),
  }),
}));

vi.mock('@/composables/api/balances/blockchain', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    queryBlockchainBalances: vi.fn().mockResolvedValue(1),
  }),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({
      result: {
        perAccount: {},
        totals: {
          assets: {},
          liabilities: {},
        },
      },
      meta: { title: '' },
    }),
    isTaskRunning: vi.fn(),
  }),
}));

vi.mock('@/composables/info/chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return ({
    useSupportedChains: vi.fn().mockReturnValue({
      supportedChains: computed<SupportedChains>(() => [
        {
          evmChainName: 'ethereum',
          id: Blockchain.ETH,
          type: 'evm',
          name: 'Ethereum',
          image: '',
          nativeToken: 'ETH',
        } satisfies EvmChainInfo,
      ]),
      getChain: () => Blockchain.ETH,
      getChainName: () => 'Ethereum',
      getNativeAsset: (chain: Blockchain) => chain,
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      getChainAccountType: () => 'evm',
    }),
  });
});

describe('composables::blockchain/balances/index', () => {
  setActivePinia(createPinia());
  let api: ReturnType<typeof useBlockchainBalancesApi> = useBlockchainBalancesApi();
  let blockchainBalances: ReturnType<typeof useBlockchainBalances> = useBlockchainBalances();
  const blockchainStore: ReturnType<typeof useBlockchainStore> = useBlockchainStore();

  beforeEach(() => {
    api = useBlockchainBalancesApi();
    blockchainBalances = useBlockchainBalances();
    vi.clearAllMocks();
  });

  describe('fetchBlockchainBalances', () => {
    it('all supported blockchains', async () => {
      // won't call if no account
      await blockchainBalances.fetchBlockchainBalances();

      expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(0);
      expect(api.queryBlockchainBalances).not.toHaveBeenCalledWith(false, 'eth');

      // call if there's account
      blockchainStore.updateAccounts(Blockchain.ETH, [
        createAccount(
          { address: '0x49ff149D649769033d43783E7456F626862CD160', label: null, tags: null },
          { nativeAsset: 'ETH', chain: Blockchain.ETH },
        ),
      ]);

      await blockchainBalances.fetchBlockchainBalances();

      expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(api.queryBlockchainBalances).toHaveBeenCalledWith(false, 'eth', undefined);
    });

    describe('particular blockchain', () => {
      const call = async (periodic = true) => {
        await blockchainBalances.fetchBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
            ignoreCache: true,
          },
          periodic,
        );
      };

      const assert = (times = 1) => {
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
});
