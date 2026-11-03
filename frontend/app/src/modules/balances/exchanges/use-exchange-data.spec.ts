import { bigNumberify } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { createMockExchangeBalances } from '@test/utils/test-data';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';

describe('useExchangeData', () => {
  const mockBalances = createMockExchangeBalances();
  let store: ReturnType<typeof useBalancesStore>;

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    store = useBalancesStore();
    vi.clearAllMocks();
    const { exchangeBalances } = storeToRefs(store);
    set(exchangeBalances, mockBalances);
  });

  it('should show the per exchange totals', () => {
    const { exchanges } = useExchangeData();
    const expectedResult = [{
      balances: mockBalances.coinbase,
      location: 'coinbase',
      total: bigNumberify(4000),
    }, {
      balances: mockBalances.kraken,
      location: 'kraken',
      total: bigNumberify(2000),
    }];

    expect(get(exchanges)).toMatchObject(expectedResult);
  });

  it('should not list the bank balances among the exchanges', () => {
    set(storeToRefs(store).exchangeBalances, mockBalances);
    set(storeToRefs(store).bankBalances, [{ accounts: [], balances: { EUR: createTestBalance(500, 500) }, connector: 'qonto', name: 'Main' }]);

    const { exchanges } = useExchangeData();

    expect(get(exchanges).map(exchange => exchange.location)).toEqual(['coinbase', 'kraken']);
  });

  it('should respect the asset association per asset breakdown', () => {
    const { useAssetBreakdown } = useAssetBalancesBreakdown();
    const breakdown = useAssetBreakdown('ETH');

    updateGeneralSettings({
      treatEth2AsEth: false,
    });

    expect(get(breakdown)).toMatchObject([{
      address: '',
      amount: bigNumberify(2000),
      location: 'coinbase',
      value: bigNumberify(2000),
    }, {
      address: '',
      amount: bigNumberify(1000),
      location: 'kraken',
      value: bigNumberify(1000),
    }]);

    updateGeneralSettings({
      treatEth2AsEth: true,
    });

    expect(get(breakdown)).toMatchObject([{
      address: '',
      amount: bigNumberify(4000),
      location: 'coinbase',
      value: bigNumberify(4000),
    }, {
      address: '',
      amount: bigNumberify(2000),
      location: 'kraken',
      value: bigNumberify(2000),
    }]);
  });
});
