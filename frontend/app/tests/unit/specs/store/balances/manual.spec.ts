import {
  TRADE_LOCATION_BANKS,
  TRADE_LOCATION_BLOCKCHAIN
} from '@/data/defaults';
import { type AssetPrices } from '@/types/prices';
import { bigNumberify } from '@/utils/bignumbers';
import { BalanceType } from '@/types/balances';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    exchangeRate: vi.fn().mockReturnValue(1)
  })
}));

vi.mock('@/composables/api/balances/manual', () => ({
  useManualBalancesApi: vi.fn().mockReturnValue({
    queryManualBalances: vi.fn().mockResolvedValue(1),
    addManualBalances: vi.fn().mockResolvedValue(1),
    editManualBalances: vi.fn().mockResolvedValue(1),
    deleteManualBalances: vi.fn().mockResolvedValue({})
  })
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

describe('store::balances/manual', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useManualBalancesStore> =
    useManualBalancesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const balances = [
    {
      id: 1,
      usdValue: bigNumberify(50),
      amount: bigNumberify(50),
      asset: 'DAI',
      label: 'My monero wallet',
      tags: [],
      location: TRADE_LOCATION_BLOCKCHAIN,
      balanceType: BalanceType.ASSET
    },
    {
      id: 2,
      usdValue: bigNumberify(30),
      amount: bigNumberify(30),
      asset: 'BTC',
      label: 'My another wallet',
      tags: [],
      location: TRADE_LOCATION_BLOCKCHAIN,
      balanceType: BalanceType.ASSET
    },
    {
      id: 3,
      usdValue: bigNumberify(50),
      amount: bigNumberify(50),
      asset: 'EUR',
      label: 'My Bank Account',
      tags: [],
      location: TRADE_LOCATION_BANKS,
      balanceType: BalanceType.LIABILITY
    }
  ];

  describe('computed', () => {
    const { manualBalancesData } = storeToRefs(store);
    set(manualBalancesData, balances);

    test('manualBalances', () => {
      const { manualBalances } = storeToRefs(store);
      expect(get(manualBalances)).toMatchObject([balances[0], balances[1]]);
    });

    test('manualLiabilities', () => {
      const { manualLiabilities } = storeToRefs(store);
      expect(get(manualLiabilities)).toMatchObject([balances[2]]);
    });

    test('manualLabels', () => {
      const { manualLabels } = storeToRefs(store);
      expect(get(manualLabels)).toMatchObject([
        'My monero wallet',
        'My another wallet',
        'My Bank Account'
      ]);
    });

    test('manualBalanceByLocation', () => {
      const { manualBalanceByLocation } = storeToRefs(store);
      expect(get(manualBalanceByLocation)).toMatchObject([
        { location: TRADE_LOCATION_BLOCKCHAIN, usdValue: bigNumberify(80) }
      ]);
    });

    test('getBreakdown', () => {
      expect(get(store.getBreakdown('BTC'))).toMatchObject([
        {
          address: '',
          location: TRADE_LOCATION_BLOCKCHAIN,
          balance: { amount: bigNumberify(30), usdValue: bigNumberify(30) },
          tags: []
        }
      ]);

      expect(get(store.getBreakdown('DAI'))).toMatchObject([
        {
          address: '',
          location: TRADE_LOCATION_BLOCKCHAIN,
          balance: { amount: bigNumberify(50), usdValue: bigNumberify(50) },
          tags: []
        }
      ]);
    });

    test('getLocationBreakdown', () => {
      expect(
        get(store.getLocationBreakdown(TRADE_LOCATION_BLOCKCHAIN))
      ).toMatchObject({ DAI: balances[0], BTC: balances[1] });
    });
  });

  describe('fetchManualBalances', () => {
    const mockBalancesResponse = [
      {
        id: 1,
        usdValue: '50',
        amount: '50',
        asset: 'DAI',
        label: 'My monero wallet',
        tags: [],
        location: TRADE_LOCATION_BLOCKCHAIN,
        balanceType: BalanceType.ASSET
      },
      {
        id: 2,
        usdValue: '30',
        amount: '30',
        asset: 'BTC',
        label: 'My another wallet',
        tags: [],
        location: TRADE_LOCATION_BLOCKCHAIN,
        balanceType: BalanceType.ASSET
      },
      {
        id: 3,
        usdValue: '50',
        amount: '50',
        asset: 'EUR',
        label: 'My Bank Account',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.LIABILITY
      }
    ];

    test('default', async () => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: { balances: mockBalancesResponse },
        meta: { title: '' }
      });

      await store.fetchManualBalances();
      expect(useManualBalancesApi().queryManualBalances).toHaveBeenCalledOnce();
      const { manualBalancesData } = storeToRefs(store);

      expect(get(manualBalancesData)).toEqual(balances);
    });
  });

  describe('updatePrices', () => {
    test('default', () => {
      const prices: AssetPrices = {
        DAI: {
          isCurrentCurrency: true,
          isManualPrice: false,
          value: bigNumberify(2)
        },
        BTC: {
          isCurrentCurrency: true,
          isManualPrice: false,
          value: bigNumberify(3)
        }
      };

      store.updatePrices(prices);
      const { manualBalancesData } = storeToRefs(store);
      expect(get(manualBalancesData)[0].usdValue).toEqual(
        bigNumberify(50).multipliedBy(2)
      );

      expect(get(manualBalancesData)[1].usdValue).toEqual(
        bigNumberify(30).multipliedBy(3)
      );

      expect(get(manualBalancesData)[2].usdValue).toEqual(
        bigNumberify(50).multipliedBy(1)
      );
    });
  });

  describe('addManualBalances', () => {
    test('default', async () => {
      await store.addManualBalance(balances[0]);

      expect(useManualBalancesApi().addManualBalances).toHaveBeenCalledWith([
        balances[0]
      ]);
    });
  });

  describe('editManualBalances', () => {
    test('default', async () => {
      await store.editManualBalance(balances[0]);

      expect(useManualBalancesApi().editManualBalances).toHaveBeenCalledWith([
        balances[0]
      ]);
    });
  });

  describe('deleteManualBalances', () => {
    test('default', async () => {
      await store.deleteManualBalance(1);

      expect(useManualBalancesApi().deleteManualBalances).toHaveBeenCalledWith([
        1
      ]);
    });
  });
});
