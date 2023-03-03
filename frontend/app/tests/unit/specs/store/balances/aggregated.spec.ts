import { type AssetBalanceWithPrice } from '@rotki/common';
import sortBy from 'lodash/sortBy';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { type BtcBalances } from '@/types/blockchain/balances';
import { useCurrencies } from '@/types/currencies';
import { SupportedExchange } from '@/types/exchanges';
import { bigNumberify, zeroBalance } from '@/utils/bignumbers';
import '../../../i18n';
import { BalanceType } from '@/types/balances';
import { type BtcAccountData } from '@/types/blockchain/accounts';
import { updateGeneralSettings } from '../../../utils/general-settings';

describe('store::balances/aggregated', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  test('aggregatedBalances', () => {
    const { connectedExchanges, exchangeBalances } = storeToRefs(
      useExchangeBalancesStore()
    );
    set(connectedExchanges, [
      {
        location: SupportedExchange.KRAKEN,
        name: 'Bitrex Acc'
      }
    ]);

    set(exchangeBalances, {
      [SupportedExchange.KRAKEN]: {
        DAI: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        },
        BTC: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        },
        ETH: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        },
        EUR: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        }
      }
    });

    const { prices } = storeToRefs(useBalancePricesStore());
    set(prices, {
      DAI: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false
      },
      EUR: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false
      },
      SAI: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false
      },
      ETH: {
        value: bigNumberify(3000),
        isManualPrice: false,
        isCurrentCurrency: false
      },
      BTC: {
        value: bigNumberify(40000),
        isManualPrice: false,
        isCurrentCurrency: false
      }
    });

    const { manualBalancesData } = storeToRefs(useManualBalancesStore());
    set(manualBalancesData, [
      {
        id: 1,
        usdValue: bigNumberify(50),
        amount: bigNumberify(50),
        asset: 'DAI',
        label: '123',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.ASSET
      }
    ]);

    const store = useAggregatedBalancesStore();
    const { balances } = store;
    const { totals } = storeToRefs(store);
    const { totals: ethTotals } = storeToRefs(useEthBalancesStore());

    const totalsState = {
      ...get(totals),
      ETH: {
        DAI: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        BTC: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        ETH: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        SAI: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        }
      }
    };

    set(ethTotals, totalsState);

    const actualResult = sortBy(get(balances()), 'asset');

    const expectedResult = sortBy(
      [
        {
          asset: 'EUR',
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
          usdPrice: bigNumberify(1)
        },
        {
          asset: 'DAI',
          amount: bigNumberify(200),
          usdValue: bigNumberify(200),
          usdPrice: bigNumberify(1)
        },
        {
          asset: 'BTC',
          amount: bigNumberify(150),
          usdValue: bigNumberify(150),
          usdPrice: bigNumberify(40000)
        },
        {
          asset: 'ETH',
          amount: bigNumberify(150),
          usdValue: bigNumberify(150),
          usdPrice: bigNumberify(3000)
        },
        {
          asset: 'SAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100),
          usdPrice: bigNumberify(1)
        }
      ] as AssetBalanceWithPrice[],
      'asset'
    );

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('btcAccounts', () => {
    const accounts: BtcAccountData = {
      standalone: [
        {
          address: '123',
          tags: null,
          label: null
        }
      ],
      xpubs: [
        {
          xpub: 'xpub123',
          addresses: [
            {
              address: '1234',
              tags: null,
              label: null
            }
          ],
          tags: null,
          label: null,
          derivationPath: 'm'
        },
        {
          xpub: 'xpub1234',
          derivationPath: null,
          label: '123',
          tags: ['a'],
          addresses: null
        }
      ]
    };
    const btcBalances: BtcBalances = {
      standalone: {
        '123': { usdValue: bigNumberify(10), amount: bigNumberify(10) }
      },
      xpubs: [
        {
          xpub: 'xpub123',
          derivationPath: 'm',
          addresses: {
            '1234': { usdValue: bigNumberify(10), amount: bigNumberify(10) }
          }
        }
      ]
    };

    const { btc } = storeToRefs(useBtcAccountsStore());
    const { balances } = storeToRefs(useBtcBalancesStore());
    const { btcAccounts } = storeToRefs(useBtcAccountBalancesStore());

    set(btc, accounts);
    set(balances, { BTC: btcBalances });

    expect(get(btcAccounts)).toEqual([
      {
        address: '123',
        balance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10)
        },
        chain: 'BTC',
        label: '',
        tags: []
      },
      {
        address: '',
        balance: zeroBalance(),
        chain: 'BTC',
        derivationPath: 'm',
        label: '',
        tags: [],
        xpub: 'xpub123'
      },
      {
        address: '1234',
        balance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10)
        },
        chain: 'BTC',
        derivationPath: 'm',
        label: '',
        tags: [],
        xpub: 'xpub123'
      },
      {
        address: '',
        balance: zeroBalance(),
        chain: 'BTC',
        derivationPath: '',
        label: '123',
        tags: ['a'],
        xpub: 'xpub1234'
      }
    ]);
  });

  test('aggregatedBalances, make sure `isCurrentCurrency` do not break the calculation', () => {
    const { connectedExchanges, exchangeBalances } = storeToRefs(
      useExchangeBalancesStore()
    );
    set(connectedExchanges, [
      {
        location: SupportedExchange.KRAKEN,
        name: 'Bitrex Acc'
      }
    ]);

    set(exchangeBalances, {
      [SupportedExchange.KRAKEN]: {
        DAI: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        },
        BTC: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        },
        ETH: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        },
        EUR: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        }
      }
    });

    const { prices } = storeToRefs(useBalancePricesStore());
    const { adjustPrices } = useBalancesStore();

    const { exchangeRates } = storeToRefs(useBalancePricesStore());
    set(exchangeRates, { EUR: bigNumberify(1.2) });

    const { currencies } = useCurrencies();
    updateGeneralSettings({
      mainCurrency: get(currencies)[1]
    });

    set(prices, {
      DAI: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false
      },
      EUR: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false
      },
      SAI: {
        value: bigNumberify(1),
        isManualPrice: false,
        isCurrentCurrency: false
      },
      ETH: {
        value: bigNumberify(3000),
        isManualPrice: false,
        isCurrentCurrency: true
      },
      BTC: {
        value: bigNumberify(40000),
        isManualPrice: false,
        isCurrentCurrency: false
      }
    });

    const { manualBalancesData } = storeToRefs(useManualBalancesStore());
    set(manualBalancesData, [
      {
        id: 1,
        usdValue: bigNumberify(50),
        amount: bigNumberify(50),
        asset: 'DAI',
        label: '123',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.ASSET
      }
    ]);

    const store = useAggregatedBalancesStore();
    const { balances } = store;
    const { totals } = storeToRefs(store);
    const { totals: ethTotals } = storeToRefs(useEthBalancesStore());

    const totalsState = {
      ...get(totals),
      ETH: {
        DAI: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        BTC: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        ETH: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        SAI: {
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        }
      }
    };

    set(ethTotals, totalsState);
    adjustPrices(get(prices));
    const actualResult = sortBy(get(balances()), 'asset');
    const expectedResult = sortBy(
      [
        {
          asset: 'EUR',
          amount: bigNumberify(50),
          usdValue: bigNumberify(50),
          usdPrice: bigNumberify(1)
        },
        {
          asset: 'DAI',
          amount: bigNumberify(200),
          usdValue: bigNumberify(200),
          usdPrice: bigNumberify(1)
        },
        {
          asset: 'BTC',
          amount: bigNumberify(150),
          usdValue: bigNumberify(6000000),
          usdPrice: bigNumberify(40000)
        },
        {
          asset: 'ETH',
          amount: bigNumberify(150),
          usdValue: bigNumberify(375000),
          usdPrice: bigNumberify(3000)
        },
        {
          asset: 'SAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100),
          usdPrice: bigNumberify(1)
        }
      ] as AssetBalanceWithPrice[],
      'asset'
    );

    expect(actualResult).toMatchObject(expectedResult);
  });
});
