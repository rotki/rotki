import { SupportedExchange } from '@/types/exchanges';
import { updateGeneralSettings } from '../../../utils/general-settings';

describe('store::balances/manual', () => {
  setActivePinia(createPinia());
  const store: ReturnType<typeof useExchangeBalancesStore> =
    useExchangeBalancesStore();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockBalances = {
    kraken: {
      ETH: {
        amount: bigNumberify(1000),
        usdValue: bigNumberify(1000)
      },
      ETH2: {
        amount: bigNumberify(1000),
        usdValue: bigNumberify(1000)
      }
    },
    coinbase: {
      ETH: {
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000)
      },
      ETH2: {
        amount: bigNumberify(2000),
        usdValue: bigNumberify(2000)
      }
    }
  };

  describe('computed', () => {
    const { exchangeBalances } = storeToRefs(store);
    set(exchangeBalances, mockBalances);

    it('exchanges', () => {
      const { exchanges } = storeToRefs(store);
      const expectedResult = [
        {
          location: SupportedExchange.COINBASE,
          balances: mockBalances.coinbase,
          total: bigNumberify(4000)
        },
        {
          location: SupportedExchange.KRAKEN,
          balances: mockBalances.kraken,
          total: bigNumberify(2000)
        }
      ];

      expect(get(exchanges)).toMatchObject(expectedResult);
    });

    it('balances', () => {
      const { balances } = storeToRefs(store);

      const expectedResult = {
        ETH: {
          amount: bigNumberify(3000),
          usdValue: bigNumberify(3000)
        },
        ETH2: {
          amount: bigNumberify(3000),
          usdValue: bigNumberify(3000)
        }
      };
      expect(get(balances)).toMatchObject(expectedResult);
    });

    it('getBreakdown', () => {
      const breakdown = store.getBreakdown('ETH');

      updateGeneralSettings({
        treatEth2AsEth: false
      });

      expect(get(breakdown)).toMatchObject([
        {
          address: '',
          location: SupportedExchange.KRAKEN,
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000)
          }
        },
        {
          address: '',
          location: SupportedExchange.COINBASE,
          balance: {
            amount: bigNumberify(2000),
            usdValue: bigNumberify(2000)
          }
        }
      ]);

      updateGeneralSettings({
        treatEth2AsEth: true
      });

      expect(get(breakdown)).toMatchObject([
        {
          address: '',
          location: SupportedExchange.KRAKEN,
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000)
          }
        },
        {
          address: '',
          location: SupportedExchange.KRAKEN,
          balance: {
            amount: bigNumberify(1000),
            usdValue: bigNumberify(1000)
          }
        },
        {
          address: '',
          location: SupportedExchange.COINBASE,
          balance: {
            amount: bigNumberify(2000),
            usdValue: bigNumberify(2000)
          }
        },
        {
          address: '',
          location: SupportedExchange.COINBASE,
          balance: {
            amount: bigNumberify(2000),
            usdValue: bigNumberify(2000)
          }
        }
      ]);
    });

    it('getLocationBreakdown', () => {
      const sessionSettingsStore = useSessionSettingsStore();
      const { connectedExchanges } = storeToRefs(sessionSettingsStore);

      set(connectedExchanges, [
        {
          name: 'Kraken',
          location: SupportedExchange.KRAKEN
        },
        {
          name: 'Coinbase',
          location: SupportedExchange.COINBASE
        }
      ]);

      updateGeneralSettings({
        treatEth2AsEth: false
      });

      const locationBreakdown = store.getLocationBreakdown(
        SupportedExchange.KRAKEN
      );

      expect(get(locationBreakdown)).toMatchObject({
        ETH: {
          asset: 'ETH',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          usdPrice: bigNumberify(-1)
        },
        ETH2: {
          asset: 'ETH2',
          amount: bigNumberify(1000),
          usdValue: bigNumberify(1000),
          usdPrice: bigNumberify(-1)
        }
      });

      updateGeneralSettings({
        treatEth2AsEth: true
      });

      expect(get(locationBreakdown)).toMatchObject({
        ETH: {
          asset: 'ETH',
          amount: bigNumberify(2000),
          usdValue: bigNumberify(2000),
          usdPrice: bigNumberify(-1)
        }
      });
    });

    it('getByLocationBalances', () => {
      const byLocationBalances = store.getByLocationBalances(bn => bn);

      expect(get(byLocationBalances)).toMatchObject({
        [SupportedExchange.COINBASE]: bigNumberify(4000),
        [SupportedExchange.KRAKEN]: bigNumberify(2000)
      });
    });
  });
});
