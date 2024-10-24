import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AssetBalanceWithBreakdown, AssetBalances } from '@/types/balances';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { AssetInfoWithId } from '@/types/asset';

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
      } satisfies AssetInfoWithId;
    }),
  }),
}));

vi.mock('@/store/balances/manual', () => ({
  useManualBalancesStore: vi.fn().mockReturnValue({
    manualBalanceByLocation: ref([]),
    assetBreakdown: vi.fn().mockReturnValue(
      computed<AssetBreakdown[]>(() => [
        {
          location: 'external',
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
          address: '',
        },
        {
          location: 'kraken',
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
          address: '',
        },
      ]),
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed<AssetBalances>(() => ({
        ETH: {
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
        },
        aUSDC: {
          amount: bigNumberify(2000),
          value: bigNumberify(2000),
        },
        bUSDC: {
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
        },
      })),
    ),
  }),
}));

vi.mock('@/store/balances/exchanges', () => ({
  useExchangeBalancesStore: vi.fn().mockReturnValue({
    getBreakdown: vi.fn().mockReturnValue(
      computed<AssetBreakdown[]>(() => [
        {
          location: 'kraken',
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
          address: '',
        },
      ]),
    ),
    getLocationBreakdown: vi.fn().mockReturnValue(
      computed<AssetBalances>(() => ({
        ETH: {
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
        },
        aUSDC: {
          amount: bigNumberify(2000),
          value: bigNumberify(2000),
        },
        cUSDC: {
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
        },
      })),
    ),
    getByLocationBalances: vi.fn(),
  }),
}));

vi.mock('@/store/blockchain/index', () => ({
  useBlockchainStore: vi.fn().mockReturnValue({
    assetBreakdown: vi.fn().mockReturnValue(
      computed<AssetBreakdown[]>(() => [
        {
          location: 'ethereum',
          address: '0xaddress1',
          amount: bigNumberify(1000),
          value: bigNumberify(1000),
        },
        {
          location: 'ethereum',
          address: '0xaddress2',
          amount: bigNumberify(2000),
          value: bigNumberify(2000),
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
    const expectedResult: AssetBreakdown[] = [
      {
        location: 'ethereum',
        address: '0xaddress2',
        amount: bigNumberify(2000),
        value: bigNumberify(2000),
      },
      {
        location: 'kraken',
        amount: bigNumberify(2000),
        value: bigNumberify(2000),
        address: '',
      },
      {
        location: 'ethereum',
        address: '0xaddress1',
        amount: bigNumberify(1000),
        value: bigNumberify(1000),
      },
      {
        location: 'external',
        amount: bigNumberify(1000),
        value: bigNumberify(1000),
        address: '',
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
    const expectedResult: AssetBalanceWithBreakdown[] = [
      {
        asset: 'aUSDC',
        amount: bigNumberify(6000),
        value: bigNumberify(6000),
        price: bigNumberify(-1),
        breakdown: [
          {
            asset: 'aUSDC',
            amount: bigNumberify(4000),
            value: bigNumberify(4000),
            price: bigNumberify(-1),
          },
          {
            asset: 'bUSDC',
            amount: bigNumberify(1000),
            value: bigNumberify(1000),
            price: bigNumberify(-1),
          },
          {
            asset: 'cUSDC',
            amount: bigNumberify(1000),
            value: bigNumberify(1000),
            price: bigNumberify(-1),
          },
        ],
      },
      {
        asset: 'ETH',
        amount: bigNumberify(2000),
        value: bigNumberify(2000),
        price: bigNumberify(-1),
      },
    ];
    expect(get(locationBreakdown)).toMatchObject(expectedResult);
  });
});
