import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useBalancesBreakdown } from '@/composables/balances/breakdown';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetInfo: vi.fn().mockImplementation((identifier) => {
      const collectionId = identifier.endsWith('USDC') ? 'USDC' : identifier;
      return {
        identifier,
        evmChain: 'ethereum',
        symbol: identifier,
        isCustomAsset: false,
        name: `Name ${identifier}`,
        collectionId,
      };
    }),
    assetSymbol: vi.fn().mockImplementation(identifier => identifier),
  }),
}));

vi.mock('@/store/balances/manual', async () => {
  const { ref, computed } = await import('vue');
  return {
    useManualBalancesStore: vi.fn().mockReturnValue({
      manualBalanceByLocation: ref([]),
      assetBreakdown: vi.fn().mockReturnValue(computed(() => [
        {
          location: 'external',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          address: '',
          tags: null,
        },
        {
          location: 'kraken',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          address: '',
          tags: null,
        },
      ])),
      getLocationBreakdown: vi.fn().mockReturnValue(computed(() => ({
        GNO: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
        },
        aUSDC: {
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
        },
        bUSDC: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
        },
      }))),
    }),
  };
});

vi.mock('@/store/balances/exchanges', async () => {
  const { computed } = await import('vue');
  return {
    useExchangeBalancesStore: vi.fn().mockReturnValue({
      getBreakdown: vi.fn().mockReturnValue(computed(() => [{
        location: 'kraken',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(1000),
        address: '',
        tags: null,
      }])),
      getLocationBreakdown: vi.fn().mockReturnValue(computed(() => ({
        GNO: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
        },
        aUSDC: {
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
        },
        cUSDC: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
        },
      }))),
      getByLocationBalances: vi.fn(),
    }),
  };
});

vi.mock('@/store/blockchain/index', async () => {
  const { computed } = await import('vue');
  return {
    useBlockchainStore: vi.fn().mockReturnValue({
      assetBreakdown: vi.fn().mockReturnValue(computed(() => [
        {
          location: 'ethereum',
          address: '0xaddress1',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          tags: null,
        },
        {
          location: 'ethereum',
          address: '0xaddress2',
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
          tags: null,
        },
      ])),
    }),
  };
});

describe('composables::balances/breakdown', () => {
  setActivePinia(createPinia());
  let balancesBreakdown: ReturnType<typeof useBalancesBreakdown> = useBalancesBreakdown();

  beforeEach(() => {
    balancesBreakdown = useBalancesBreakdown();
  });

  it('assetBreakdown', () => {
    const assetBreakdown = balancesBreakdown.assetBreakdown('GNO');
    const expectedResult = [
      {
        location: 'ethereum',
        address: '0xaddress2',
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000),
        tags: null,
      },
      {
        location: 'kraken',
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000),
        address: '',
        tags: null,
      },
      {
        location: 'ethereum',
        address: '0xaddress1',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(1000),
        tags: null,
      },
      {
        location: 'external',
        amount: bigNumberify(1000),
        usdValue: bigNumberify(1000),
        address: '',
        tags: null,
      },
    ];

    expect(get(assetBreakdown)).toMatchObject(expectedResult);
  });

  it('locationBreakdown', () => {
    const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
    set(fetchedAssetCollections, {
      USDC: {
        name: 'USDC',
        symbol: 'USDC',
        mainAsset: 'USDC',
      },
      GNO: {
        name: 'GNO',
        symbol: 'GNO',
        mainAsset: 'GNO',
      },
    });
    const locationBreakdown = balancesBreakdown.locationBreakdown('kraken');
    const expectedResult = [
      {
        asset: 'USDC',
        amount: bigNumberify(6000),
        usdValue: bigNumberify(6000),
        usdPrice: bigNumberify(-1),
        breakdown: [
          {
            asset: 'aUSDC',
            amount: bigNumberify(4000),
            usdValue: bigNumberify(4000),
            usdPrice: bigNumberify(-1),
          },
          {
            asset: 'bUSDC',
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
            usdPrice: bigNumberify(-1),
          },
          {
            asset: 'cUSDC',
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
            usdPrice: bigNumberify(-1),
          },
        ],
      },
      {
        asset: 'GNO',
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000),
        usdPrice: bigNumberify(-1),
        breakdown: [
          {
            asset: 'GNO',
            amount: bigNumberify(2000),
            usdValue: bigNumberify(2000),
            usdPrice: bigNumberify(-1),
          },
        ],
      },
    ];
    expect(get(locationBreakdown)).toStrictEqual(expectedResult);
  });
});
