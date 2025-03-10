import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useSessionSettingsStore } from '@/store/settings/session';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { updateGeneralSettings } from '../../../utils/general-settings';

describe('store::balances/manual', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useExchangeBalancesStore> = useExchangeBalancesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockBalances = {
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
  };

  describe('computed', () => {
    const { exchangeBalances } = storeToRefs(store);
    set(exchangeBalances, mockBalances);

    it('exchanges', () => {
      const { exchanges } = storeToRefs(store);
      const expectedResult = [
        {
          location: 'coinbase',
          balances: mockBalances.coinbase,
          total: bigNumberify(4000),
        },
        {
          location: 'kraken',
          balances: mockBalances.kraken,
          total: bigNumberify(2000),
        },
      ];

      expect(get(exchanges)).toMatchObject(expectedResult);
    });

    it('balances', () => {
      const { balances } = storeToRefs(store);

      const expectedResult = {
        ETH: {
          amount: bigNumberify(3000),
          usdValue: bigNumberify(3000),
        },
        ETH2: {
          amount: bigNumberify(3000),
          usdValue: bigNumberify(3000),
        },
      };
      expect(get(balances)).toMatchObject(expectedResult);
    });

    it('getBreakdown', () => {
      const breakdown = store.getBreakdown('ETH');

      updateGeneralSettings({
        treatEth2AsEth: false,
      });

      expect(get(breakdown)).toMatchObject([
        {
          address: '',
          location: 'kraken',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
        },
        {
          address: '',
          location: 'coinbase',
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
        },
      ]);

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(breakdown)).toMatchObject([
        {
          address: '',
          location: 'kraken',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
        },
        {
          address: '',
          location: 'kraken',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
        },
        {
          address: '',
          location: 'coinbase',
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
        },
        {
          address: '',
          location: 'coinbase',
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
        },
      ]);
    });

    it('getLocationBreakdown', () => {
      const sessionSettingsStore = useSessionSettingsStore();
      const { connectedExchanges } = storeToRefs(sessionSettingsStore);

      set(connectedExchanges, [
        {
          name: 'Kraken',
          location: 'kraken',
        },
        {
          name: 'Coinbase',
          location: 'coinbase',
        },
      ]);

      updateGeneralSettings({
        treatEth2AsEth: false,
      });

      const locationBreakdown = store.getLocationBreakdown('kraken');

      expect(get(locationBreakdown)).toMatchObject({
        ETH: {
          asset: 'ETH',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          usdPrice: bigNumberify(-1),
        },
        ETH2: {
          asset: 'ETH2',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          usdPrice: bigNumberify(-1),
        },
      });

      updateGeneralSettings({
        treatEth2AsEth: true,
      });

      expect(get(locationBreakdown)).toMatchObject({
        ETH: {
          asset: 'ETH',
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
          usdPrice: bigNumberify(-1),
        },
      });
    });

    it('getByLocationBalances', () => {
      const byLocationBalances = store.getByLocationBalances(bn => bn);

      expect(get(byLocationBalances)).toMatchObject({
        coinbase: bigNumberify(4000),
        kraken: bigNumberify(2000),
      });
    });
  });
});
