import type { EvmChainInfo } from '@/types/api/chains';
import type { AssetBreakdown, BlockchainAccount } from '@/types/blockchain/accounts';
import type { BlockchainBalances } from '@/types/blockchain/balances';
import type { ExchangeData } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useLocationBalancesBreakdown } from '@/modules/balances/use-location-balances-breakdown';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useBlockchainStore } from '@/store/blockchain';
import { useSessionSettingsStore } from '@/store/settings/session';
import { BalanceType } from '@/types/balances';
import { type AssetBalanceWithPrice, bigNumberify, type Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/composables/info/chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: () => Blockchain.ETH,
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      getChainName: () => 'Ethereum',
      getEvmChainName: (_chain: string) => 'ethereum',
      getNativeAsset: (chain: Blockchain) => chain,
      isEvmLikeChains: (_chain: string) => false,
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

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetInfo: vi.fn().mockImplementation((identifier) => {
      const collectionId = identifier.endsWith('USDC') ? 'USDC' : identifier;
      return {
        collectionId,
        evmChain: 'ethereum',
        identifier,
        isCustomAsset: false,
        name: `Name ${identifier}`,
        symbol: identifier,
      };
    }),
    assetSymbol: vi.fn().mockImplementation(identifier => identifier),
  }),
}));

const testManualBalances: ManualBalanceWithValue[] = [{
  amount: bigNumberify(500),
  asset: 'aUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 1,
  label: 'test 1',
  location: 'external',
  tags: [],
  usdValue: bigNumberify(500),
}, {
  amount: bigNumberify(500),
  asset: 'bUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 2,
  label: 'test 2',
  location: 'external',
  tags: [],
  usdValue: bigNumberify(500),
}, {
  amount: bigNumberify(1000),
  asset: 'GNO',
  balanceType: BalanceType.ASSET,
  identifier: 3,
  label: 'test 3',
  location: 'kraken',
  tags: [],
  usdValue: bigNumberify(1000),
}, {
  amount: bigNumberify(500),
  asset: 'aUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 4,
  label: 'test 4',
  location: 'kraken',
  tags: [],
  usdValue: bigNumberify(500),
}, {
  amount: bigNumberify(500),
  asset: 'bUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 5,
  label: 'test 5',
  location: 'kraken',
  tags: [],
  usdValue: bigNumberify(500),
}];

const testExchangeBalances: ExchangeData = {
  kraken: {
    aUSDC: {
      amount: bigNumberify(2000),
      usdValue: bigNumberify(2000),
    },
    cUSDC: {
      amount: bigNumberify(1000),
      usdValue: bigNumberify(1000),
    },
    GNO: {
      amount: bigNumberify(1000),
      usdValue: bigNumberify(1000),
    },
  },
};

const testEthereumBalances: BlockchainBalances = {
  perAccount: {
    eth: {
      '0xaddress1': {
        assets: {
          aUSDC: {
            amount: bigNumberify(400),
            usdValue: bigNumberify(400),
          },
          cUSDC: {
            amount: bigNumberify(300),
            usdValue: bigNumberify(300),
          },
          GNO: {
            amount: bigNumberify(300),
            usdValue: bigNumberify(300),
          },

        },
        liabilities: {},
      },
      '0xaddress2': {
        assets: {
          aUSDC: {
            amount: bigNumberify(800),
            usdValue: bigNumberify(800),
          },
          cUSDC: {
            amount: bigNumberify(800),
            usdValue: bigNumberify(800),
          },
          GNO: {
            amount: bigNumberify(400),
            usdValue: bigNumberify(400),
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

const testAccounts: BlockchainAccount[] = [{
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

describe('composables::balances/breakdown', () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    const { exchangeBalances, manualBalances } = storeToRefs(useBalancesStore());
    const { updateAccounts, updateBalances } = useBlockchainStore();
    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
    set(connectedExchanges, [{
      location: 'kraken',
      name: 'Kraken 1',
    }]);
    set(manualBalances, testManualBalances);
    set(exchangeBalances, testExchangeBalances);
    updateBalances('eth', testEthereumBalances);
    updateAccounts('eth', testAccounts);
    await nextTick();
  });

  it('should give an accurate breakdown for the asset', () => {
    const { useAssetBreakdown } = useAssetBalancesBreakdown();
    const assetBreakdown = useAssetBreakdown('GNO');
    const expectedResult: AssetBreakdown[] = [{
      address: '',
      amount: bigNumberify(2000),
      location: 'kraken',
      tags: undefined,
      usdValue: bigNumberify(2000),
    }, {
      address: '0xaddress2',
      amount: bigNumberify(400),
      location: 'ethereum',
      tags: undefined,
      usdValue: bigNumberify(400),
    }, {
      address: '0xaddress1',
      amount: bigNumberify(300),
      location: 'ethereum',
      tags: undefined,
      usdValue: bigNumberify(300),
    }];

    expect(get(assetBreakdown)).toMatchObject(expectedResult);
  });

  it('locationBreakdown', () => {
    const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
    const { useLocationBreakdown } = useLocationBalancesBreakdown();
    set(fetchedAssetCollections, {
      GNO: {
        mainAsset: 'GNO',
        name: 'GNO',
        symbol: 'GNO',
      },
      USDC: {
        mainAsset: 'USDC',
        name: 'USDC',
        symbol: 'USDC',
      },
    });
    const locationBreakdown = useLocationBreakdown('kraken');
    const expectedResult: AssetBalanceWithPrice[] = [{
      amount: bigNumberify(4000),
      asset: 'USDC',
      breakdown: [{
        amount: bigNumberify(2500),
        asset: 'aUSDC',
        usdPrice: bigNumberify(-1),
        usdValue: bigNumberify(2500),
      }, {
        amount: bigNumberify(500),
        asset: 'bUSDC',
        usdPrice: bigNumberify(-1),
        usdValue: bigNumberify(500),
      }, {
        amount: bigNumberify(1000),
        asset: 'cUSDC',
        usdPrice: bigNumberify(-1),
        usdValue: bigNumberify(1000),
      }],
      usdPrice: bigNumberify(-1),
      usdValue: bigNumberify(4000),
    }, {
      amount: bigNumberify(2000),
      asset: 'GNO',
      breakdown: [{
        amount: bigNumberify(2000),
        asset: 'GNO',
        usdPrice: bigNumberify(-1),
        usdValue: bigNumberify(2000),
      }],
      usdPrice: bigNumberify(-1),
      usdValue: bigNumberify(2000),
    }];
    expect(get(locationBreakdown)).toStrictEqual(expectedResult);
  });
});
