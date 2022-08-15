import { AssetBalanceWithPrice } from '@rotki/common';
import { get, set } from '@vueuse/core';
import sortBy from 'lodash/sortBy';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { BalanceType, BtcBalances } from '@/services/balances/types';
import { BtcAccountData } from '@/services/types-api';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancePricesStore } from '@/store/balances/prices';
import { SupportedExchange } from '@/types/exchanges';
import { bigNumberify, zeroBalance } from '@/utils/bignumbers';

describe('balances:getters', () => {
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
      DAI: bigNumberify(1),
      EUR: bigNumberify(1),
      SAI: bigNumberify(1),
      ETH: bigNumberify(3000),
      BTC: bigNumberify(40000)
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

    const { blockchainTotalsState, aggregatedBalances } = storeToRefs(
      useBlockchainBalancesStore()
    );

    const mockBlockchainTotalsState = {
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
    };

    set(blockchainTotalsState, mockBlockchainTotalsState);

    const actualResult = sortBy(get(aggregatedBalances), 'asset');

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

  test('manualLabels', () => {
    const { manualBalancesData, manualLabels } = storeToRefs(
      useManualBalancesStore()
    );
    set(manualBalancesData, [
      {
        id: 1,
        usdValue: bigNumberify(50),
        amount: bigNumberify(50),
        asset: 'DAI',
        label: 'My monero wallet',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.ASSET
      },
      {
        id: 2,
        usdValue: bigNumberify(50),
        amount: bigNumberify(50),
        asset: 'EUR',
        label: 'My Bank Account',
        tags: [],
        location: TRADE_LOCATION_BANKS,
        balanceType: BalanceType.ASSET
      }
    ]);
    expect(
      // @ts-ignore
      get(manualLabels)
    ).toMatchObject(['My monero wallet', 'My Bank Account']);
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
    const balances: BtcBalances = {
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

    const { btcAccountsState, btcAccounts } = storeToRefs(
      useBlockchainAccountsStore()
    );
    const { btcBalancesState } = storeToRefs(useBlockchainBalancesStore());

    set(btcAccountsState, accounts);
    set(btcBalancesState, balances);

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
});
