import { bigNumberify } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { createMockExchangeBalances } from '@test/utils/test-data';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';

describe('useExchangeData', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useBalancesStore> = useBalancesStore();
  const mockBalances = createMockExchangeBalances();

  beforeEach(() => {
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

  it('should show the per asset balances', () => {
    const { useBaseExchangeBalances } = useExchangeData();

    expect(get(useBaseExchangeBalances())).toMatchObject({
      ETH: {
        coinbase: createTestBalance(2000, 2000),
        kraken: createTestBalance(1000, 1000),
      },
      ETH2: {
        coinbase: createTestBalance(2000, 2000),
        kraken: createTestBalance(1000, 1000),
      },
    });
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
      usdValue: bigNumberify(2000),
    }, {
      address: '',
      amount: bigNumberify(1000),
      location: 'kraken',
      usdValue: bigNumberify(1000),
    }]);

    updateGeneralSettings({
      treatEth2AsEth: true,
    });

    expect(get(breakdown)).toMatchObject([{
      address: '',
      amount: bigNumberify(4000),
      location: 'coinbase',
      usdValue: bigNumberify(4000),
    }, {
      address: '',
      amount: bigNumberify(2000),
      location: 'kraken',
      usdValue: bigNumberify(2000),
    }]);
  });
});
