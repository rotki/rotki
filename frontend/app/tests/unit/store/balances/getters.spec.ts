import { AssetBalance, AssetBalanceWithPrice } from '@rotki/common';
import { SupportedAsset } from '@rotki/common/lib/data';
import sortBy from 'lodash/sortBy';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { BalanceType, BtcBalances } from '@/services/balances/types';
import { BtcAccountData } from '@/services/types-api';
import { BalanceGetters, getters } from '@/store/balances/getters';
import { BalanceState } from '@/store/balances/types';
import { SessionState } from '@/store/session/types';
import store from '@/store/store';
import { RotkehlchenState } from '@/store/types';
import { SupportedExchange } from '@/types/exchanges';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { stub } from '../../../common/utils';

describe('balances:getters', () => {
  test('aggregatedBalances', () => {
    const mockGetters = {
      exchangeBalances: function (): AssetBalance[] {
        return [
          {
            asset: 'DAI',
            amount: bigNumberify(50),
            usdValue: bigNumberify(50)
          },
          {
            asset: 'BTC',
            amount: bigNumberify(50),
            usdValue: bigNumberify(50)
          },
          {
            asset: 'ETH',
            amount: bigNumberify(50),
            usdValue: bigNumberify(50)
          },
          {
            asset: 'EUR',
            amount: bigNumberify(50),
            usdValue: bigNumberify(50)
          }
        ];
      },
      totals: [
        {
          asset: 'DAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        {
          asset: 'BTC',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        {
          asset: 'ETH',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        },
        {
          asset: 'SAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        }
      ]
    };

    const state: BalanceState = stub<BalanceState>({
      manualBalances: [
        {
          usdValue: bigNumberify(50),
          amount: bigNumberify(50),
          asset: 'DAI',
          label: '123',
          tags: [],
          location: TRADE_LOCATION_BANKS,
          balanceType: BalanceType.LIABILITY
        }
      ],
      manualLiabilities: [],
      prices: {
        DAI: bigNumberify(1),
        EUR: bigNumberify(1),
        SAI: bigNumberify(1),
        ETH: bigNumberify(3000),
        BTC: bigNumberify(40000)
      },
      connectedExchanges: [
        {
          location: SupportedExchange.BITTREX,
          name: 'Bitrex Acc'
        }
      ]
    });

    const actualResult = sortBy(
      getters.aggregatedBalances(
        state,
        stub<BalanceGetters>(mockGetters),
        stub<RotkehlchenState>({
          session: stub<SessionState>({
            ignoredAssets: []
          })
        }),
        stub()
      ),
      'asset'
    );

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
    expect(
      // @ts-ignore
      getters.manualLabels({
        manualBalances: [
          {
            asset: 'XMR',
            label: 'My monero wallet',
            amount: '50.315',
            tags: ['public'],
            location: 'blockchain'
          },
          {
            asset: 'EUR',
            label: 'My Bank Account',
            amount: '150',
            tags: [],
            location: 'banks'
          }
        ],
        manualLiabilities: []
      })
    ).toMatchObject(['My monero wallet', 'My Bank Account']);
  });

  test('assetInfo', () => {
    const eth: SupportedAsset = {
      identifier: 'ETH',
      name: 'Ethereum',
      started: 1438214400,
      symbol: 'ETH',
      coingecko: '',
      cryptocompare: '',
      assetType: 'own chain'
    };

    // @ts-ignore
    const actual = getters.assetInfo({
      supportedAssets: [eth]
    });
    expect(actual('ETH')).toMatchObject(eth);
    expect(actual('BTC')).toBeUndefined();
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
    store.commit('balances/btcAccounts', accounts);
    store.commit('balances/updateBtc', balances);

    expect(store.getters['balances/btcAccounts']).toEqual([
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
        balance: {
          amount: Zero,
          usdValue: Zero
        },
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
        balance: {
          amount: Zero,
          usdValue: Zero
        },
        chain: 'BTC',
        derivationPath: '',
        label: '123',
        tags: ['a'],
        xpub: 'xpub1234'
      }
    ]);
  });
});
