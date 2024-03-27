import { Blockchain } from '@rotki/common/lib/blockchain';
import { computed } from 'vue';
import { Section } from '@/types/status';
import type { EvmChainInfo, SupportedChains } from '@/types/api/chains';

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

vi.mock('@/composables/info/chains', () => ({
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
  }),
}));

describe('composables::blockchain/balances/index', () => {
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
      await blockchainBalances.fetchBlockchainBalances();

      expect(api.queryBlockchainBalances).toHaveBeenCalledTimes(1);
      expect(api.queryBlockchainBalances).toHaveBeenCalledWith(false, 'eth');
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
        expect(api.queryBlockchainBalances).toHaveBeenCalledWith(
          true,
          Blockchain.ETH,
        );
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
