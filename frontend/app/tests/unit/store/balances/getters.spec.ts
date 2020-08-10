import sortBy from 'lodash/sortBy';
import { AssetBalance } from '@/model/blockchain-balances';
import { Location } from '@/services/types-common';
import { SupportedAsset } from '@/services/types-model';
import { getters } from '@/store/balances/getters';
import { BalanceState } from '@/store/balances/state';
import { bigNumberify } from '@/utils/bignumbers';
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
          location: Location.BANKS
        }
      ],
      connectedExchanges: ['bittrex']
    });

    const actualResult = sortBy(
      getters.aggregatedBalances(state, mockGetters, stub(), stub()),
      'asset'
    );

    const expectedResult = sortBy(
      [
        {
          asset: 'EUR',
          amount: bigNumberify(50),
          usdValue: bigNumberify(50)
        },
        {
          asset: 'DAI',
          amount: bigNumberify(200),
          usdValue: bigNumberify(200)
        },
        {
          asset: 'BTC',
          amount: bigNumberify(150),
          usdValue: bigNumberify(150)
        },
        {
          asset: 'ETH',
          amount: bigNumberify(150),
          usdValue: bigNumberify(150)
        },
        {
          asset: 'SAI',
          amount: bigNumberify(100),
          usdValue: bigNumberify(100)
        }
      ] as AssetBalance[],
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
        ]
      })
    ).toMatchObject(['My monero wallet', 'My Bank Account']);
  });

  test('assetInfo', () => {
    const eth: SupportedAsset = {
      key: 'ETH',
      name: 'Ethereum',
      started: 1438214400,
      symbol: 'ETH',
      type: 'own chain'
    };

    // @ts-ignore
    const actual = getters.assetInfo({
      supportedAssets: [eth]
    });
    expect(actual('ETH')).toMatchObject(eth);
    expect(actual('BTC')).toBeUndefined();
  });
});
