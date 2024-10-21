import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetInfo: vi.fn().mockImplementation((identifier) => {
      const collectionId = identifier.endsWith('USDC') ? 'USDC' : undefined;
      return {
        identifier,
        evmChain: 'ethereum',
        symbol: identifier,
        isCustomAsset: false,
        name: `Name ${identifier}`,
        collectionId,
      };
    }),
  }),
}));

vi.mock('@/store/balances/manual', () => ({
  useManualBalancesStore: vi.fn().mockReturnValue({
    manualBalanceByLocation: ref([]),
    assetBreakdown: vi.fn().mockReturnValue(
      computed(() => [
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
      ]),
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed(() => ({
        ETH: {
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
      })),
    ),
  }),
}));

vi.mock('@/store/balances/exchanges', () => ({
  useExchangeBalancesStore: vi.fn().mockReturnValue({
    getBreakdown: vi.fn().mockReturnValue(
      computed(() => [
        {
          location: 'kraken',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          address: '',
          tags: null,
        },
      ]),
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed(() => ({
        ETH: {
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
      })),
    ),
    getByLocationBalances: vi.fn(),
  }),
}));

vi.mock('@/store/blockchain/index', () => ({
  useBlockchainStore: vi.fn().mockReturnValue({
    assetBreakdown: vi.fn().mockReturnValue(
      computed(() => [
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
      ]),
    ),
  }),
}));

describe('composables::balances/breakdown', () => {
  setActivePinia(createPinia());
  let balancesBreakdown: ReturnType<typeof useBalancesBreakdown> = useBalancesBreakdown();

  beforeEach(() => {
    balancesBreakdown = useBalancesBreakdown();
  });

  it('assetBreakdown', () => {
    const assetBreakdown = balancesBreakdown.assetBreakdown('ETH');
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
      },
    });
    const locationBreakdown = balancesBreakdown.locationBreakdown('kraken');
    const expectedResult = [
      {
        asset: 'aUSDC',
        amount: bigNumberify(6000),
        usdValue: bigNumberify(6000),
        price: bigNumberify(-1),
        breakdown: [
          {
            asset: 'aUSDC',
            amount: bigNumberify(4000),
            usdValue: bigNumberify(4000),
            price: bigNumberify(-1),
          },
          {
            asset: 'bUSDC',
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
            price: bigNumberify(-1),
          },
          {
            asset: 'cUSDC',
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
            price: bigNumberify(-1),
          },
        ],
      },
      {
        asset: 'ETH',
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000),
        price: bigNumberify(-1),
      },
    ];
    expect(get(locationBreakdown)).toMatchObject(expectedResult);
  });
});
