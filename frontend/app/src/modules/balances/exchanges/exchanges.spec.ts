import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useLocationBalancesBreakdown } from '@/modules/balances/use-location-balances-breakdown';
import { useSessionSettingsStore } from '@/store/settings/session';
import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('store::balances/exchanges', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useBalancesStore> = useBalancesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockBalances = {
    coinbase: {
      ETH: {
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000),
      },
      ETH2: {
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000),
      },
    },
    kraken: {
      ETH: {
        amount: bigNumberify(1000),
        usdValue: bigNumberify(1000),
      },
      ETH2: {
        amount: bigNumberify(1000),
        usdValue: bigNumberify(1000),
      },
    },
  };

  describe('computed', () => {
    const { exchangeBalances } = storeToRefs(store);
    set(exchangeBalances, mockBalances);

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
      const { balances } = useExchangeData();

      const expectedResult = {
        ETH: {
          coinbase: {
            amount: bigNumberify(2000),
            usdValue: bigNumberify(2000),
          },
          kraken: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
          },
        },
        ETH2: {
          coinbase: {
            amount: bigNumberify(2000),
            usdValue: bigNumberify(2000),
          },
          kraken: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000),
          },
        },
      };
      expect(get(balances)).toMatchObject(expectedResult);
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

    it('should respect the asset association for the location breakdown', async () => {
      const sessionSettingsStore = useSessionSettingsStore();
      const { useLocationBreakdown } = useLocationBalancesBreakdown();
      const { connectedExchanges } = storeToRefs(sessionSettingsStore);

      set(connectedExchanges, [{
        location: 'kraken',
        name: 'Kraken',
      }, {
        location: 'coinbase',
        name: 'Coinbase',
      }]);

      updateGeneralSettings({ treatEth2AsEth: false });

      const locationBreakdown = useLocationBreakdown('kraken');

      expect(get(locationBreakdown)).toMatchObject([{
        amount: bigNumberify(1000),
        asset: 'ETH',
        usdPrice: bigNumberify(-1),
        usdValue: bigNumberify(1000),
      }, {
        amount: bigNumberify(1000),
        asset: 'ETH2',
        usdPrice: bigNumberify(-1),
        usdValue: bigNumberify(1000),
      }]);

      updateGeneralSettings({ treatEth2AsEth: true });

      await nextTick();

      expect(get(locationBreakdown)).toMatchObject([{
        amount: bigNumberify(2000),
        asset: 'ETH',
        usdPrice: bigNumberify(-1),
        usdValue: bigNumberify(2000),
      }]);
    });
  });
});
