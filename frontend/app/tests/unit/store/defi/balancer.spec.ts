import { BalancerBalance } from '@rotki/common/lib/defi/balancer';
import { XswapPool } from '@rotki/common/lib/defi/xswap';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { useBalancerStore } from '@/store/defi/balancer';
import { bigNumberify } from '@/utils/bignumbers';

export const setBalancerBalances = () => {
  const { balances } = storeToRefs(useBalancerStore());
  set(balances, {
    '0xc45c9537cc44f973174016E1bc30D65E11205A2A': [
      {
        address: '0x49ff149D649769033d43783E7456F626862CD160',
        tokens: [
          {
            token: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          },
          {
            token: 'eip155:1/erc20:0x408e41876cCCDC0F92210600ef50372656052a38',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(2000),
            weight: '50'
          },
          {
            token: 'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          }
        ],
        totalAmount: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(4000)
        }
      },
      {
        address: '0xc409D34aCcb279620B1acDc05E408e287d543d17',
        tokens: [
          {
            token: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(4500)
            },
            usdPrice: bigNumberify(4500),
            weight: '45.0'
          },
          {
            token: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(2000),
            weight: '20'
          },
          {
            token: 'eip155:1/erc20:0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(3500)
            },
            usdPrice: bigNumberify(3500),
            weight: '35.0'
          }
        ],
        totalAmount: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10000)
        }
      }
    ],
    '0xfa7576a5FEC5cfaDBFcDB5596f74a64C1f998c65': [
      {
        address: '0x49ff149D649769033d43783E7456F626862CD160',
        tokens: [
          {
            token: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          },
          {
            token: 'eip155:1/erc20:0x408e41876cCCDC0F92210600ef50372656052a38',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(4000)
            },
            usdPrice: bigNumberify(2000),
            weight: '50'
          },
          {
            token: 'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          }
        ],
        totalAmount: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(20),
          usdValue: bigNumberify(8000)
        }
      }
    ]
  });
};

describe('balancer', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
    setBalancerBalances();
  });

  test('aggregatedBalances', () => {
    const store = useBalancerStore();
    const { balancerBalances } = store;

    const expectedResult: BalancerBalance[] = [
      {
        address: '0x49ff149D649769033d43783E7456F626862CD160',
        tokens: [
          {
            token: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          },
          {
            token: 'eip155:1/erc20:0x408e41876cCCDC0F92210600ef50372656052a38',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(6000)
            },
            usdPrice: bigNumberify(2000),
            weight: '50'
          },
          {
            token: 'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          }
        ],
        totalAmount: bigNumberify(20000),
        userBalance: { amount: bigNumberify(30), usdValue: bigNumberify(12000) }
      },
      {
        address: '0xc409D34aCcb279620B1acDc05E408e287d543d17',
        tokens: [
          {
            token: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(4500)
            },
            usdPrice: bigNumberify(4500),
            weight: '45.0'
          },
          {
            token: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(2000),
            weight: '20'
          },
          {
            token: 'eip155:1/erc20:0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(3500)
            },
            usdPrice: bigNumberify(3500),
            weight: '35.0'
          }
        ],
        totalAmount: bigNumberify(20000),
        userBalance: { amount: bigNumberify(10), usdValue: bigNumberify(10000) }
      }
    ];

    const actualResult = get(balancerBalances([]));

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('filter balances by address', () => {
    const store = useBalancerStore();
    const { balancerBalances } = store;

    const expectedResult: BalancerBalance[] = [
      {
        address: '0x49ff149D649769033d43783E7456F626862CD160',
        tokens: [
          {
            token: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          },
          {
            token: 'eip155:1/erc20:0x408e41876cCCDC0F92210600ef50372656052a38',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(2000),
            weight: '50'
          },
          {
            token: 'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000)
            },
            usdPrice: bigNumberify(1000),
            weight: '25.0'
          }
        ],
        totalAmount: bigNumberify(20000),
        userBalance: { amount: bigNumberify(10), usdValue: bigNumberify(4000) }
      },
      {
        address: '0xc409D34aCcb279620B1acDc05E408e287d543d17',
        tokens: [
          {
            token: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(4500)
            },
            usdPrice: bigNumberify(4500),
            weight: '45.0'
          },
          {
            token: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(2000),
            weight: '20'
          },
          {
            token: 'eip155:1/erc20:0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(3500)
            },
            usdPrice: bigNumberify(3500),
            weight: '35.0'
          }
        ],
        totalAmount: bigNumberify(20000),
        userBalance: { amount: bigNumberify(10), usdValue: bigNumberify(10000) }
      }
    ];

    const actualResult = get(
      balancerBalances(['0xc45c9537cc44f973174016E1bc30D65E11205A2A'])
    );

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('addresses', () => {
    const store = useBalancerStore();
    const { addresses } = storeToRefs(store);

    const expectedResult: string[] = [
      '0xc45c9537cc44f973174016E1bc30D65E11205A2A',
      '0xfa7576a5FEC5cfaDBFcDB5596f74a64C1f998c65'
    ];

    const actualResult = get(addresses);

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('pools', () => {
    const store = useBalancerStore();
    const { pools } = storeToRefs(store);

    const expectedResult: XswapPool[] = [
      {
        address: '0x49ff149D649769033d43783E7456F626862CD160',
        assets: [
          'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
          'eip155:1/erc20:0x408e41876cCCDC0F92210600ef50372656052a38',
          'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA'
        ]
      },
      {
        address: '0xc409D34aCcb279620B1acDc05E408e287d543d17',
        assets: [
          'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
          'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
          'eip155:1/erc20:0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D'
        ]
      }
    ];

    const actualResult = get(pools);

    expect(actualResult).toMatchObject(expectedResult);
  });
});
