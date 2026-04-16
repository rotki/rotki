import type { AssetPrices } from '@/modules/assets/prices/price-types';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Currency, CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useManualBalancesApi } from '@/modules/balances/api/use-manual-balances-api';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { BalanceType } from '@/modules/balances/types/balances';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN } from '@/modules/core/common/defaults';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const runTaskMock = vi.fn();

vi.mock('@/modules/balances/api/use-manual-balances-api', () => ({
  useManualBalancesApi: vi.fn().mockReturnValue({
    addManualBalances: vi.fn().mockResolvedValue(1),
    deleteManualBalances: vi.fn().mockResolvedValue({}),
    editManualBalances: vi.fn().mockResolvedValue(1),
    queryManualBalances: vi.fn().mockResolvedValue(1),
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
      await taskFn();
      return runTaskMock(taskFn, ...rest);
    },
    cancelTask: vi.fn(),
    cancelTaskByTaskType: vi.fn(),
  }),
}));

interface ManualBalance extends Omit<ManualBalanceWithValue, 'amount' | 'value'> {
  amount: string;
  value: string;
}

function toParsed(balance: ManualBalance): ManualBalanceWithValue {
  return {
    ...balance,
    amount: bigNumberify(balance.amount),
    value: bigNumberify(balance.value),
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
  value: '50',
}, {
  amount: '30',
  asset: 'BTC',
  balanceType: BalanceType.ASSET,
  identifier: 2,
  label: 'My another wallet',
  location: TRADE_LOCATION_BLOCKCHAIN,
  tags: [],
  value: '30',
}, {
  amount: '60',
  asset: 'EUR',
  balanceType: BalanceType.LIABILITY,
  identifier: 3,
  label: 'My Bank Account',
  location: TRADE_LOCATION_BANKS,
  tags: [],
  value: '60',
}];

async function updateBalances(balances: ManualBalance[]): Promise<void> {
  const { fetchManualBalances } = useManualBalances();
  runTaskMock.mockResolvedValue({ success: true, result: { balances } });

  await fetchManualBalances(true);
  await nextTick();
}

const ethPrice = {
  isManualPrice: false,
  oracle: 'coingecko',
  value: bigNumberify(1),
};

describe('store::balances/manual', () => {
  let store: ReturnType<typeof useBalancesStore>;

  beforeAll(async () => {
    setActivePinia(createPinia());
    store = useBalancesStore();
    const { exchangeRates, prices } = storeToRefs(useBalancePricesStore());
    const generalSettingsStore = useGeneralSettingsStore();
    generalSettingsStore.update({
      ...generalSettingsStore.settings,
      mainCurrency: new Currency('US Dollar', CURRENCY_USD, '$'),
    });
    set(exchangeRates, { USD: bigNumberify(1) });
    set(prices, {
      ETH: ethPrice,
      ETH2: ethPrice,
    });
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
        { location: TRADE_LOCATION_BLOCKCHAIN, value: bigNumberify(80) },
      ]);
    });
  });

  it('should update the prices for all assets and liabilities', () => {
    const newPrices: AssetPrices = {
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
      EUR: {
        isManualPrice: false,
        oracle: 'coingecko',
        value: bigNumberify(1),
      },
    };

    // Update the price store so balance price calculations can find the prices
    const { prices } = storeToRefs(useBalancePricesStore());
    set(prices, newPrices);

    store.updatePrices(newPrices);
    const { manualBalances, manualLiabilities } = storeToRefs(store);
    expect(get(manualBalances)[0].value).toEqual(bigNumberify(50).multipliedBy(2));
    expect(get(manualBalances)[1].value).toEqual(bigNumberify(30).multipliedBy(3));
    expect(get(manualLiabilities)[0].value).toEqual(bigNumberify(60).multipliedBy(1));
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
