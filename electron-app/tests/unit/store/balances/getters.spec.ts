import { AssetBalance } from '@/model/blockchain-balances';
import { getters } from '@/store/balances/getters';
import { bigNumberify } from '@/utils/bignumbers';

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
    const state = {
      fiatBalances: [
        {
          usdValue: bigNumberify(50),
          amount: bigNumberify(50),
          currency: 'EUR'
        }
      ],
      connectedExchanges: ['bittrex']
    };

    // @ts-ignore
    expect(getters.aggregatedBalances(state, mockGetters)).toMatchObject([
      {
        asset: 'EUR',
        amount: bigNumberify(100),
        usdValue: bigNumberify(100)
      },
      {
        asset: 'DAI',
        amount: bigNumberify(150),
        usdValue: bigNumberify(150)
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
    ] as AssetBalance[]);
  });
});
