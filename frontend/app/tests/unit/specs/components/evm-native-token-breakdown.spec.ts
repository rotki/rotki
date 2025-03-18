import type { useAssetIconApi } from '@/composables/api/assets/icon';
import type { EvmChainInfo } from '@/types/api/chains';
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import type { BlockchainBalances } from '@/types/blockchain/balances';
import type { ExchangeData } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import EvmNativeTokenBreakdown from '@/components/EvmNativeTokenBreakdown.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { BalanceType } from '@/types/balances';
import { bigNumberify, type Blockchain } from '@rotki/common';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { libraryDefaults } from '../../utils/provide-defaults';

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

vi.mock('@/composables/info/chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: () => Blockchain.ETH,
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      getChainName: () => 'Ethereum',
      getEvmChainName: (chain: string) => {
        if (chain.startsWith('eth')) {
          return 'ethereum';
        }
        else if (chain.startsWith('opt')) {
          return 'optimism';
        }
        return undefined;
      },
      getNativeAsset: (chain: Blockchain) => chain,
      isEvmLikeChains: (_chain: string) => false,
      matchChain: (chain: string) => {
        if (chain.toLowerCase() === 'ethereum') {
          return Blockchain.ETH;
        }
        else if (chain.toLowerCase() === 'optimism') {
          return Blockchain.OPTIMISM;
        }
        else {
          return undefined;
        }
      },
      txChains: computed(() => [{
        evmChainName: 'ethereum',
        id: Blockchain.ETH,
        image: '',
        name: 'Ethereum',
        nativeToken: 'ETH',
        type: 'evm',
      } satisfies EvmChainInfo]),
    }),
  };
});

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn().mockReturnValue({
    checkAsset: vi.fn().mockResolvedValue(404),
    assetImageUrl: vi.fn(),
  } satisfies Partial<ReturnType<typeof useAssetIconApi>>),
}));

vi.mock('@/composables/locations', () => ({
  useLocations: vi.fn().mockReturnValue({
    locationData: vi.fn().mockImplementation((identifier) => {
      const val = get(identifier);
      return computed(() => ({
        identifier: val,
        name: val,
      }));
    }),
  }),
}));

const testManualBalances: ManualBalanceWithValue[] = [{
  amount: bigNumberify(500),
  asset: 'ETH',
  balanceType: BalanceType.ASSET,
  identifier: 1,
  label: 'test 1',
  location: 'external',
  tags: [],
  usdValue: bigNumberify(500),
}, {
  amount: bigNumberify(500),
  asset: 'ETH',
  balanceType: BalanceType.ASSET,
  identifier: 2,
  label: 'test 2',
  location: 'kraken',
  tags: [],
  usdValue: bigNumberify(500),
}];

const testExchangeBalances: ExchangeData = {
  kraken: {
    ETH: {
      amount: bigNumberify(1000),
      usdValue: bigNumberify(1000),
    },
  },
};

const testEthereumAccounts: BlockchainAccount[] = [{
  chain: 'eth',
  data: {
    address: '0xaddress1',
    type: 'address',
  },
  nativeAsset: 'ETH',
}, {
  chain: 'eth',
  data: {
    address: '0xaddress2',
    type: 'address',
  },
  nativeAsset: 'ETH',
}];

const testEthereumBalances: BlockchainBalances = {
  perAccount: {
    eth: {
      '0xaddress1': {
        assets: {
          ETH: {
            amount: bigNumberify(400),
            usdValue: bigNumberify(400),
          },
        },
        liabilities: {},
      },
      '0xaddress2': {
        assets: {
          ETH: {
            amount: bigNumberify(800),
            usdValue: bigNumberify(800),
          },
        },
        liabilities: {},
      },
    },
  },
  totals: {
    assets: {},
    liabilities: {},
  },
};

const testOptimismAccounts: BlockchainAccount[] = [{
  chain: 'opt',
  data: {
    address: '0xaddress3',
    type: 'address',
  },
  nativeAsset: 'ETH',
}];

const testOptimismBalances: BlockchainBalances = {
  perAccount: {
    opt: {
      '0xaddress1': {
        assets: {
          ETH: {
            amount: bigNumberify(123),
            usdValue: bigNumberify(123),
          },
        },
        liabilities: {},
      },
    },
  },
  totals: {
    assets: {},
    liabilities: {},
  },
};

describe('evmNativeTokenBreakdown.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof EvmNativeTokenBreakdown>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);

    const { updateAccounts } = useBlockchainAccountsStore();
    const { updateBalances } = useBalancesStore();
    const { manualBalances, exchangeBalances } = storeToRefs(useBalancesStore());
    set(manualBalances, testManualBalances);
    set(exchangeBalances, testExchangeBalances);
    updateBalances('eth', testEthereumBalances);
    updateAccounts('eth', testEthereumAccounts);
    updateBalances('opt', testOptimismBalances);
    updateAccounts('opt', testOptimismAccounts);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof EvmNativeTokenBreakdown>) =>
    mount(EvmNativeTokenBreakdown, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
      },
      ...options,
    });

  it('should show correct entries', async () => {
    wrapper = createWrapper({ props: { identifier: 'ETH', assets: [] } });
    await nextTick();
    const expectedResult = [{
      location: 'kraken',
      amount: bigNumberify(1500),
      usdValue: bigNumberify(1500),
    }, {
      location: 'ethereum',
      amount: bigNumberify(1200),
      usdValue: bigNumberify(1200),
    }, {
      location: 'external',
      amount: bigNumberify(500),
      usdValue: bigNumberify(500),
    }, {
      location: 'optimism',
      amount: bigNumberify(123),
      usdValue: bigNumberify(123),
    }];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(3)').text()).toBe(result.amount.toFormat(2));
      expect(tr.find('td:nth-child(4)').text()).toContain(result.usdValue.toFormat(2));
    });
  });

  it('should show correct entries for blockchainOnly=true', async () => {
    wrapper = createWrapper({
      props: { identifier: 'ETH', blockchainOnly: true, assets: [] },
    });
    await nextTick();
    const expectedResult = [{
      location: 'ethereum',
      amount: bigNumberify(1200),
      usdValue: bigNumberify(1200),
    }, {
      location: 'optimism',
      amount: bigNumberify(123),
      usdValue: bigNumberify(123),
    }];

    expectedResult.forEach((result, index) => {
      const tr = wrapper.find(`tbody tr:nth-child(${index + 1})`);
      expect(tr.find('td:first-child').text()).toBe(result.location);
      expect(tr.find('td:nth-child(3)').text()).toBe(result.amount.toFormat(2));
      expect(tr.find('td:nth-child(4)').text()).toContain(result.usdValue.toFormat(2));
    });
  });
});
