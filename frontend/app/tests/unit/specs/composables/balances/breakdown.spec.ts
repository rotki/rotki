vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetInfo: vi.fn().mockImplementation(identifier => {
      const collectionId = identifier.endsWith('USDC') ? 'USDC' : undefined;
      return {
        identifier,
        evmChain: 'ethereum',
        symbol: identifier,
        isCustomAsset: false,
        name: `Name ${identifier}`,
        collectionId
      };
    })
  })
}));

vi.mock('@/store/balances/manual', () => ({
  useManualBalancesStore: vi.fn().mockReturnValue({
    manualBalanceByLocation: ref([]),
    getBreakdown: vi.fn().mockReturnValue(
      computed(() => [
        {
          location: 'external',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000)
          },
          address: '',
          tags: null
        },
        {
          location: 'kraken',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000)
          },
          address: '',
          tags: null
        }
      ])
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed(() => ({
        ETH: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000)
        },
        aUSDC: {
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000)
        },
        bUSDC: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000)
        }
      }))
    )
  })
}));

vi.mock('@/store/balances/exchanges', () => ({
  useExchangeBalancesStore: vi.fn().mockReturnValue({
    getBreakdown: vi.fn().mockReturnValue(
      computed(() => [
        {
          location: 'kraken',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000)
          },
          address: '',
          tags: null
        }
      ])
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed(() => ({
        ETH: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000)
        },
        aUSDC: {
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000)
        },
        cUSDC: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000)
        }
      }))
    ),
    getByLocationBalances: vi.fn()
  })
}));

vi.mock('@/composables/blockchain/account-balances/index', () => ({
  useAccountBalances: vi.fn().mockReturnValue({
    getBreakdown: vi.fn().mockReturnValue(
      computed(() => [
        {
          location: 'ethereum',
          address: '0xaddres',
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000)
          },
          tags: null
        }
      ])
    )
  })
}));

describe('composables::balances/breakdown', () => {
  setActivePinia(createPinia());
  let balancesBreakdown: ReturnType<typeof useBalancesBreakdown> =
    useBalancesBreakdown();

  beforeEach(() => {
    balancesBreakdown = useBalancesBreakdown();
  });

  it('assetBreakdown', () => {
    const assetBreakdown = balancesBreakdown.assetBreakdown('ETH');
    const expectedResult = [
      {
        location: 'kraken',
        balance: { amount: bigNumberify(2000), usdValue: bigNumberify(2000) },
        address: '',
        tags: null
      },
      {
        location: 'ethereum',
        address: '0xaddres',
        balance: { amount: bigNumberify(1000), usdValue: bigNumberify(1000) },
        tags: null
      },
      {
        location: 'external',
        balance: { amount: bigNumberify(1000), usdValue: bigNumberify(1000) },
        address: '',
        tags: null
      }
    ];

    expect(get(assetBreakdown)).toMatchObject(expectedResult);
  });

  it('locationBreakdown', () => {
    const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
    set(fetchedAssetCollections, {
      USDC: {
        name: 'USDC',
        symbol: 'USDC'
      }
    });
    const locationBreakdown = balancesBreakdown.locationBreakdown('kraken');
    const expectedResult = [
      {
        asset: 'aUSDC',
        amount: bigNumberify(6000),
        usdValue: bigNumberify(6000),
        usdPrice: bigNumberify(-1),
        breakdown: [
          {
            asset: 'aUSDC',
            amount: bigNumberify(4000),
            usdValue: bigNumberify(4000),
            usdPrice: bigNumberify(-1)
          },
          {
            asset: 'bUSDC',
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
            usdPrice: bigNumberify(-1)
          },
          {
            asset: 'cUSDC',
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
            usdPrice: bigNumberify(-1)
          }
        ]
      },
      {
        asset: 'ETH',
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000),
        usdPrice: bigNumberify(-1)
      }
    ];
    expect(get(locationBreakdown)).toMatchObject(expectedResult);
  });
});
