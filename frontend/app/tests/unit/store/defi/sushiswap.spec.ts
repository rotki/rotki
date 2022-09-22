import { XswapBalance, XswapPool } from '@rotki/common/lib/defi/xswap';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { bigNumberify } from '@/utils/bignumbers';

export const setSushiswapBalances = () => {
  const { balances } = storeToRefs(useSushiswapStore());
  set(balances, {
    '0xf9D0D04829D54C1175C8c13a08763aD1570b1B46': [
      {
        address: '0x6a091a3406E0073C3CD6340122143009aDac0EDa',
        assets: [
          {
            asset: 'eip155:1/erc20:0x767FE9EDC9E0dF98E07454847909b5E959D7ca0E',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1500)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(25),
          usdValue: bigNumberify(2500)
        }
      }
    ],
    '0xFEB7e72357116275a6960c5243f33D94B1c673fA': [
      {
        address: '0x6a091a3406E0073C3CD6340122143009aDac0EDa',
        assets: [
          {
            asset: 'eip155:1/erc20:0x767FE9EDC9E0dF98E07454847909b5E959D7ca0E',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(50),
          usdValue: bigNumberify(5000)
        }
      }
    ]
  });
};

describe('sushiswap', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
    setSushiswapBalances();
  });

  test('aggregatedBalances', () => {
    const store = useSushiswapStore();
    const { balanceList } = store;

    const expectedResult: XswapBalance[] = [
      {
        account: '0xf9D0D04829D54C1175C8c13a08763aD1570b1B46',
        userBalance: { amount: bigNumberify(75), usdValue: bigNumberify(7500) },
        totalSupply: bigNumberify(20000),
        assets: [
          {
            asset: 'eip155:1/erc20:0x767FE9EDC9E0dF98E07454847909b5E959D7ca0E',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(4500)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        address: '0x6a091a3406E0073C3CD6340122143009aDac0EDa'
      }
    ];

    const actualResult = get(balanceList([]));

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('filter balances by address', () => {
    const store = useSushiswapStore();
    const { balanceList } = store;

    const expectedResult: XswapBalance[] = [
      {
        account: '0xFEB7e72357116275a6960c5243f33D94B1c673fA',
        userBalance: { amount: bigNumberify(50), usdValue: bigNumberify(5000) },
        totalSupply: bigNumberify(20000),
        assets: [
          {
            asset: 'eip155:1/erc20:0x767FE9EDC9E0dF98E07454847909b5E959D7ca0E',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        address: '0x6a091a3406E0073C3CD6340122143009aDac0EDa'
      }
    ];

    const actualResult = get(
      balanceList(['0xFEB7e72357116275a6960c5243f33D94B1c673fA'])
    );

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('addresses', () => {
    const store = useSushiswapStore();
    const { addresses } = storeToRefs(store);

    const expectedResult: string[] = [
      '0xf9D0D04829D54C1175C8c13a08763aD1570b1B46',
      '0xFEB7e72357116275a6960c5243f33D94B1c673fA'
    ];

    const actualResult = get(addresses);

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('pools', () => {
    const store = useSushiswapStore();
    const { pools } = storeToRefs(store);

    const expectedResult: XswapPool[] = [
      {
        address: '0x6a091a3406E0073C3CD6340122143009aDac0EDa',
        assets: [
          'eip155:1/erc20:0x767FE9EDC9E0dF98E07454847909b5E959D7ca0E',
          'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
        ]
      }
    ];

    const actualResult = get(pools);

    expect(actualResult).toMatchObject(expectedResult);
  });
});
