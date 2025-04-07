import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';
import { useManualBalancesApi } from '@/composables/api/balances/manual';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN, TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useLocationBalancesBreakdown } from '@/modules/balances/use-location-balances-breakdown';
import { useTaskStore } from '@/store/tasks';
import { BalanceType } from '@/types/balances';
import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/balances/prices', async () => {
  const { bigNumberify } = await import('@rotki/common');
  return ({
    useBalancePricesStore: vi.fn().mockReturnValue({
      assetPrice: vi.fn().mockReturnValue(bigNumberify(1)),
      exchangeRate: vi.fn().mockReturnValue(1),
    }),
  });
});

vi.mock('@/composables/api/balances/manual', () => ({
  useManualBalancesApi: vi.fn().mockReturnValue({
    addManualBalances: vi.fn().mockResolvedValue(1),
    deleteManualBalances: vi.fn().mockResolvedValue({}),
    editManualBalances: vi.fn().mockResolvedValue(1),
    queryManualBalances: vi.fn().mockResolvedValue(1),
  }),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({}),
  }),
}));

interface ManualBalance extends Omit<ManualBalanceWithValue, 'usdValue' | 'amount'> {
  usdValue: string;
  amount: string;
}

function toParsed(balance: ManualBalance): ManualBalanceWithValue {
  return {
    ...balance,
    amount: bigNumberify(balance.amount),
    usdValue: bigNumberify(balance.usdValue),
  };
}

const balances: ManualBalance[] = [{
  amount: '50',
  asset: 'DAI',
  balanceType: BalanceType.ASSET,
  identifier: 1,
  label: 'My monero wallet',
  location: TRADE_LOCATION_BLOCKCHAIN,
  tags: [],
  usdValue: '50',
}, {
  amount: '30',
  asset: 'BTC',
  balanceType: BalanceType.ASSET,
  identifier: 2,
  label: 'My another wallet',
  location: TRADE_LOCATION_BLOCKCHAIN,
  tags: [],
  usdValue: '30',
}, {
  amount: '60',
  asset: 'EUR',
  balanceType: BalanceType.LIABILITY,
  identifier: 3,
  label: 'My Bank Account',
  location: TRADE_LOCATION_BANKS,
  tags: [],
  usdValue: '60',
}];

const ethAndEth2Balances: ManualBalance[] = [{
  amount: '50',
  asset: 'ETH',
  balanceType: BalanceType.ASSET,
  identifier: 4,
  label: 'Ethereum',
  location: TRADE_LOCATION_EXTERNAL,
  tags: [],
  usdValue: '50',
}, {
  amount: '100',
  asset: 'ETH2',
  balanceType: BalanceType.ASSET,
  identifier: 5,
  label: 'Staked ETH',
  location: TRADE_LOCATION_EXTERNAL,
  tags: [],
  usdValue: '100',
}];

async function updateBalances(balances: ManualBalance[]): Promise<void> {
  const { fetchManualBalances } = useManualBalances();
  vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
    meta: { title: '' },
    result: { balances },
  });

  await fetchManualBalances(true);
  await nextTick();
}

describe('store::balances/manual', () => {
  let store: ReturnType<typeof useBalancesStore>;

  beforeAll(() => {
    setActivePinia(createPinia());
    store = useBalancesStore();
  });

  beforeEach(async () => {
    vi.clearAllMocks();
    await updateBalances(balances);
  });

  describe('aggregating data based on manual balances and liabilities', () => {
    it('should update manualBalances based on the result', () => {
      const { manualBalances } = storeToRefs(store);
      expect(get(manualBalances)).toMatchObject([balances[0], balances[1]].map(toParsed));
    });

    it('should update manualLiabilities based on the result', () => {
      const { manualLiabilities } = storeToRefs(store);
      expect(get(manualLiabilities)).toMatchObject([toParsed(balances[2])]);
    });

    it('should aggregate the labels from all the manual balances and liabilities', () => {
      const { manualLabels } = useManualBalanceData();
      expect(get(manualLabels)).toMatchObject(['My monero wallet', 'My another wallet', 'My Bank Account']);
    });

    it('should show the total balance of a location', () => {
      const { manualBalanceByLocation } = useManualBalanceData();
      expect(get(manualBalanceByLocation)).toMatchObject([
        { location: TRADE_LOCATION_BLOCKCHAIN, usdValue: bigNumberify(80) },
      ]);
    });

    it('should return the breakdown of liabilities', () => {
      const { useAssetBreakdown } = useAssetBalancesBreakdown();
      expect(get(useAssetBreakdown('EUR', true))).toMatchObject([{
        address: '',
        amount: bigNumberify(60),
        location: TRADE_LOCATION_BANKS,
        tags: undefined,
        usdValue: bigNumberify(60),
      }]);
    });

    it('should return the breakdown of assets', async () => {
      const { useAssetBreakdown } = useAssetBalancesBreakdown();
      expect(get(useAssetBreakdown('BTC'))).toMatchObject([{
        address: '',
        amount: bigNumberify(30),
        location: TRADE_LOCATION_BLOCKCHAIN,
        tags: undefined,
        usdValue: bigNumberify(30),
      }]);

      expect(get(useAssetBreakdown('DAI'))).toMatchObject([{
        address: '',
        amount: bigNumberify(50),
        location: TRADE_LOCATION_BLOCKCHAIN,
        tags: undefined,
        usdValue: bigNumberify(50),
      }]);

      // Breakdown for liabilities
      expect(get(useAssetBreakdown('EUR'))).toMatchObject([]);
      await updateBalances(ethAndEth2Balances);

      const breakdown = useAssetBreakdown('ETH');

      updateGeneralSettings({
        treatEth2AsEth: false,
      });

      await nextTick();

      expect(get(breakdown)).toMatchObject([{
        address: '',
        amount: bigNumberify(50),
        location: 'external',
        tags: undefined,
        usdValue: bigNumberify(50),
      }]);

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(breakdown)).toMatchObject([{
        address: '',
        amount: bigNumberify(150),
        location: 'external',
        tags: undefined,
        usdValue: bigNumberify(150),
      }]);
    });

    it('getLocationBreakdown', async () => {
      await updateBalances(ethAndEth2Balances);
      const { useLocationBreakdown } = useLocationBalancesBreakdown();

      updateGeneralSettings({ treatEth2AsEth: false });

      const breakdown = useLocationBreakdown(TRADE_LOCATION_EXTERNAL);

      expect(get(breakdown)).toMatchObject([{
        amount: bigNumberify(100),
        asset: 'ETH2',
        usdPrice: bigNumberify(1),
        usdValue: bigNumberify(100),
      }, {
        amount: bigNumberify(50),
        asset: 'ETH',
        usdPrice: bigNumberify(1),
        usdValue: bigNumberify(50),
      }]);

      updateGeneralSettings({ treatEth2AsEth: true });

      expect(get(breakdown)).toMatchObject([{
        amount: bigNumberify(150),
        asset: 'ETH',
        usdPrice: bigNumberify(1),
        usdValue: bigNumberify(150),
      }]);
    });
  });

  it('should update the prices for all assets and liabilities', () => {
    const prices: AssetPrices = {
      BTC: {
        isManualPrice: false,
        oracle: 'coingecko',
        value: bigNumberify(3),
      },
      DAI: {
        isManualPrice: false,
        oracle: 'coingecko',
        value: bigNumberify(2),
      },
    };

    store.updatePrices(prices);
    const { manualBalances, manualLiabilities } = storeToRefs(store);
    expect(get(manualBalances)[0].usdValue).toEqual(bigNumberify(50).multipliedBy(2));
    expect(get(manualBalances)[1].usdValue).toEqual(bigNumberify(30).multipliedBy(3));
    expect(get(manualLiabilities)[0].usdValue).toEqual(bigNumberify(60).multipliedBy(1));
  });

  describe('should run create/update/delete operations', () => {
    const balance = toParsed(balances[0]);
    it('should add manual balance', async () => {
      const { addManualBalance } = useManualBalances();
      await addManualBalance(balance);
      expect(useManualBalancesApi().addManualBalances).toHaveBeenCalledWith([balance]);
    });

    it('should edit manual balance', async () => {
      const { editManualBalance } = useManualBalances();
      await editManualBalance(balance);
      expect(useManualBalancesApi().editManualBalances).toHaveBeenCalledWith([balance]);
    });

    it('should delete manual balance', async () => {
      const { deleteManualBalance } = useManualBalances();
      await deleteManualBalance(1);
      expect(useManualBalancesApi().deleteManualBalances).toHaveBeenCalledWith([1]);
    });
  });
});
