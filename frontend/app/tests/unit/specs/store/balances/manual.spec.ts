import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN, TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { type AssetBalances, BalanceType } from '@/types/balances';
import { updateGeneralSettings } from '../../../utils/general-settings';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';
import type { AssetBreakdown } from '@/types/blockchain/accounts';

vi.mock('@/store/balances/prices', () => ({
  useBalancePricesStore: vi.fn().mockReturnValue({
    exchangeRate: vi.fn().mockReturnValue(1),
  }),
}));

vi.mock('@/composables/api/balances/manual', () => ({
  useManualBalancesApi: vi.fn().mockReturnValue({
    queryManualBalances: vi.fn().mockResolvedValue(1),
    addManualBalances: vi.fn().mockResolvedValue(1),
    editManualBalances: vi.fn().mockResolvedValue(1),
    deleteManualBalances: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({}),
  }),
}));

describe('store::balances/manual', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useManualBalancesStore> = useManualBalancesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const balances: ManualBalanceWithValue[] = [
    {
      identifier: 1,
      value: bigNumberify(50),
      amount: bigNumberify(50),
      asset: 'DAI',
      label: 'My monero wallet',
      tags: [],
      location: TRADE_LOCATION_BLOCKCHAIN,
      balanceType: BalanceType.ASSET,
    },
    {
      identifier: 2,
      value: bigNumberify(30),
      amount: bigNumberify(30),
      asset: 'BTC',
      label: 'My another wallet',
      tags: [],
      location: TRADE_LOCATION_BLOCKCHAIN,
      balanceType: BalanceType.ASSET,
    },
    {
      identifier: 3,
      value: bigNumberify(60),
      amount: bigNumberify(60),
      asset: 'EUR',
      label: 'My Bank Account',
      tags: [],
      location: TRADE_LOCATION_BANKS,
      balanceType: BalanceType.LIABILITY,
    },
  ];

  const ethAndEth2Balances: ManualBalanceWithValue[] = [
    {
      identifier: 4,
      value: bigNumberify(50),
      amount: bigNumberify(50),
      asset: 'ETH',
      label: 'Ethereum',
      tags: [],
      location: TRADE_LOCATION_EXTERNAL,
      balanceType: BalanceType.ASSET,
    },
    {
      identifier: 5,
      value: bigNumberify(100),
      amount: bigNumberify(100),
      asset: 'ETH2',
      label: 'Staked ETH',
      tags: [],
      location: TRADE_LOCATION_EXTERNAL,
      balanceType: BalanceType.ASSET,
    },
  ];

  describe('computed', () => {
    const { manualBalancesData } = storeToRefs(store);
    set(manualBalancesData, balances);

    it('manualBalances', () => {
      const { manualBalances } = storeToRefs(store);
      expect(get(manualBalances)).toMatchObject([balances[0], balances[1]]);
    });

    it('manualLiabilities', () => {
      const { manualLiabilities } = storeToRefs(store);
      expect(get(manualLiabilities)).toMatchObject([balances[2]]);
    });

    it('manualLabels', () => {
      const { manualLabels } = storeToRefs(store);
      expect(get(manualLabels)).toMatchObject(['My monero wallet', 'My another wallet', 'My Bank Account']);
    });

    it('manualBalanceByLocation', () => {
      const { manualBalanceByLocation } = storeToRefs(store);
      expect(get(manualBalanceByLocation)).toMatchObject([
        { location: TRADE_LOCATION_BLOCKCHAIN, usdValue: bigNumberify(80) },
      ]);
    });

    it('liabilityBreakdown', () => {
      expect(get(store.liabilityBreakdown('EUR'))).toMatchObject([
        {
          address: '',
          location: TRADE_LOCATION_BANKS,
          amount: bigNumberify(60),
          value: bigNumberify(60),
          tags: [],
        },
      ] satisfies AssetBreakdown[]);
    });

    it('assetBreakdown', () => {
      expect(get(store.assetBreakdown('BTC'))).toMatchObject([
        {
          address: '',
          location: TRADE_LOCATION_BLOCKCHAIN,
          amount: bigNumberify(30),
          value: bigNumberify(30),
          tags: [],
        },
      ] satisfies AssetBreakdown[]);

      expect(get(store.assetBreakdown('DAI'))).toMatchObject([
        {
          address: '',
          location: TRADE_LOCATION_BLOCKCHAIN,
          amount: bigNumberify(50),
          value: bigNumberify(50),
          tags: [],
        },
      ] satisfies AssetBreakdown[]);

      // Breakdown for liabilities
      expect(get(store.assetBreakdown('EUR'))).toMatchObject([]);

      const { manualBalancesData } = storeToRefs(store);
      set(manualBalancesData, ethAndEth2Balances);

      const breakdown = store.assetBreakdown('ETH');

      updateGeneralSettings({
        treatEth2AsEth: false,
      });

      expect(get(breakdown)).toMatchObject([
        {
          address: '',
          location: 'external',
          amount: bigNumberify(50),
          value: bigNumberify(50),
          tags: [],
        },
      ] satisfies AssetBreakdown[]);

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(breakdown)).toMatchObject([
        {
          address: '',
          location: 'external',
          amount: bigNumberify(50),
          value: bigNumberify(50),
          tags: [],
        },
        {
          address: '',
          location: 'external',
          amount: bigNumberify(100),
          value: bigNumberify(100),
          tags: [],
        },
      ] satisfies AssetBreakdown[]);
    });

    it('getLocationBreakdown', () => {
      updateGeneralSettings({
        treatEth2AsEth: false,
      });

      const locationBreakdown = store.getLocationBreakdown(TRADE_LOCATION_EXTERNAL);

      expect(get(locationBreakdown)).toMatchObject({
        ETH: ethAndEth2Balances[0],
        ETH2: ethAndEth2Balances[1],
      });

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(locationBreakdown)).toMatchObject({
        ETH: {
          amount: bigNumberify(150),
          value: bigNumberify(150),
        },
      } satisfies AssetBalances);
    });
  });

  describe('fetchManualBalances', () => {
    const mockBalancesResponse = [
      {
        identifier: 1,
        usdValue: '50',
        amount: '50',
        asset: 'DAI',
        label: 'My monero wallet',
        tags: [],
        location: TRADE_LOCATION_BLOCKCHAIN,
        balanceType: BalanceType.ASSET,
      },
      {
        identifier: 2,
        usdValue: '30',
        amount: '30',
        asset: 'BTC',
        label: 'My another wallet',
        tags: [],
        location: TRADE_LOCATION_BLOCKCHAIN,
        balanceType: BalanceType.ASSET,
      },
      {
        identifier: 3,
        usdValue: '60',
        amount: '60',
        asset: 'EUR',
        label: 'My Bank Account',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.LIABILITY,
      },
    ];

    it('default', async () => {
      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: { balances: mockBalancesResponse },
        meta: { title: '' },
      });

      const prices: AssetPrices = {
        DAI: {
          isManualPrice: false,
          value: bigNumberify(1),
        },
        BTC: {
          isManualPrice: false,
          value: bigNumberify(1),
        },
        EUR: {
          isManualPrice: false,
          value: bigNumberify(1),
        },
      };

      await store.fetchManualBalances();
      expect(useManualBalancesApi().queryManualBalances).toHaveBeenCalledOnce();
      const { manualBalancesData } = storeToRefs(store);

      expect(get(manualBalancesData)).toEqual(balances.map(balance => ({
        ...balance,
        value: Zero,
      })));

      store.updatePrices(prices);

      expect(get(manualBalancesData)).toEqual(balances);
    });
  });

  describe('updatePrices', () => {
    it('default', () => {
      const prices: AssetPrices = {
        DAI: {
          isManualPrice: false,
          value: bigNumberify(2),
        },
        BTC: {
          isManualPrice: false,
          value: bigNumberify(3),
        },
        EUR: {
          isManualPrice: false,
          value: bigNumberify(1),
        },
      };

      store.updatePrices(prices);
      const balances = store.manualBalancesData;
      expect(balances[0].value).toEqual(balances[0].amount.multipliedBy(2));
      expect(balances[1].value).toEqual(balances[1].amount.multipliedBy(3));
      expect(balances[2].value).toEqual(balances[2].amount.multipliedBy(1));
    });
  });

  describe('addManualBalances', () => {
    it('default', async () => {
      await store.addManualBalance(balances[0]);

      expect(useManualBalancesApi().addManualBalances).toHaveBeenCalledWith([balances[0]]);
    });
  });

  describe('editManualBalances', () => {
    it('default', async () => {
      await store.editManualBalance(balances[0]);

      expect(useManualBalancesApi().editManualBalances).toHaveBeenCalledWith([balances[0]]);
    });
  });

  describe('deleteManualBalances', () => {
    it('default', async () => {
      await store.deleteManualBalance(1);

      expect(useManualBalancesApi().deleteManualBalances).toHaveBeenCalledWith([1]);
    });
  });
});
