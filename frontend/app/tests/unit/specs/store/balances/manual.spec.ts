import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';
import { useManualBalancesApi } from '@/composables/api/balances/manual';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN, TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useTaskStore } from '@/store/tasks';
import { BalanceType } from '@/types/balances';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { updateGeneralSettings } from '../../../utils/general-settings';

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
      usdValue: bigNumberify(50),
      amount: bigNumberify(50),
      asset: 'DAI',
      label: 'My monero wallet',
      tags: [],
      location: TRADE_LOCATION_BLOCKCHAIN,
      balanceType: BalanceType.ASSET,
    },
    {
      identifier: 2,
      usdValue: bigNumberify(30),
      amount: bigNumberify(30),
      asset: 'BTC',
      label: 'My another wallet',
      tags: [],
      location: TRADE_LOCATION_BLOCKCHAIN,
      balanceType: BalanceType.ASSET,
    },
    {
      identifier: 3,
      usdValue: bigNumberify(60),
      amount: bigNumberify(60),
      asset: 'EUR',
      label: 'My Bank Account',
      tags: [],
      location: TRADE_LOCATION_BANKS,
      balanceType: BalanceType.LIABILITY,
    },
  ];

  const ethAndEth2Balances = [
    {
      identifier: 4,
      usdValue: bigNumberify(50),
      amount: bigNumberify(50),
      asset: 'ETH',
      label: 'Ethereum',
      tags: [],
      location: TRADE_LOCATION_EXTERNAL,
      balanceType: BalanceType.ASSET,
    },
    {
      identifier: 5,
      usdValue: bigNumberify(100),
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
          usdValue: bigNumberify(60),
          tags: [],
        },
      ]);
    });

    it('assetBreakdown', () => {
      expect(get(store.assetBreakdown('BTC'))).toMatchObject([
        {
          address: '',
          location: TRADE_LOCATION_BLOCKCHAIN,
          amount: bigNumberify(30),
          usdValue: bigNumberify(30),
          tags: [],
        },
      ]);

      expect(get(store.assetBreakdown('DAI'))).toMatchObject([
        {
          address: '',
          location: TRADE_LOCATION_BLOCKCHAIN,
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
          tags: [],
        },
      ]);

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
          usdValue: bigNumberify(50),
          tags: [],
        },
      ]);

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(breakdown)).toMatchObject([
        {
          address: '',
          location: 'external',
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
          tags: [],
        },
        {
          address: '',
          location: 'external',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100),
          tags: [],
        },
      ]);
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
          usdValue: bigNumberify(150),
        },
      });
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

      await store.fetchManualBalances();
      expect(useManualBalancesApi().queryManualBalances).toHaveBeenCalledOnce();
      const { manualBalancesData } = storeToRefs(store);

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
      };

      store.updatePrices(prices);
      const { manualBalancesData } = storeToRefs(store);
      expect(get(manualBalancesData)[0].usdValue).toEqual(bigNumberify(50).multipliedBy(2));

      expect(get(manualBalancesData)[1].usdValue).toEqual(bigNumberify(30).multipliedBy(3));

      expect(get(manualBalancesData)[2].usdValue).toEqual(bigNumberify(60).multipliedBy(1));
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
