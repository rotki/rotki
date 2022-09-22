import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { setupLiquidityPosition } from '@/composables/defi';
import { bigNumberify } from '@/utils/bignumbers';
import { setBalancerBalances } from '../store/defi/balancer.spec';
import { setSushiswapBalances } from '../store/defi/sushiswap.spec';
import {
  setUniswapV2Balances,
  setUniswapV3Balances
} from '../store/defi/uniswap.spec';

describe('defi', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
    setUniswapV2Balances();
    setUniswapV3Balances();
    setSushiswapBalances();
    setBalancerBalances();
  });

  test('lpAggregatedBalances', () => {
    const { lpAggregatedBalances } = setupLiquidityPosition();

    const expectedResult = [
      {
        address: '0x49ff149D649769033d43783E7456F626862CD160',
        totalAmount: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(30),
          usdValue: bigNumberify(12000)
        },
        usdValue: bigNumberify(12000),
        asset: 'eip155:1/erc20:0x49ff149D649769033d43783E7456F626862CD160',
        premiumOnly: true,
        assets: [
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
        type: 'token',
        lpType: 'BALANCER',
        id: 0
      },
      {
        address: '0xc409D34aCcb279620B1acDc05E408e287d543d17',
        totalAmount: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(10000)
        },
        usdValue: bigNumberify(10000),
        asset: 'eip155:1/erc20:0xc409D34aCcb279620B1acDc05E408e287d543d17',
        premiumOnly: true,
        assets: [
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
        type: 'token',
        lpType: 'BALANCER',
        id: 1
      },
      {
        account: '0x069D2a5d415894b74C80650A5D67f09E28282B9d',
        userBalance: {
          amount: bigNumberify(1600),
          usdValue: bigNumberify(8500)
        },
        totalSupply: bigNumberify(20000),
        assets: [
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(4500)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
        usdValue: bigNumberify(8500),
        asset: 'eip155:1/erc20:0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
        premiumOnly: false,
        type: 'token',
        lpType: 'UNISWAP_V2',
        id: 2
      },
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
        address: '0x6a091a3406E0073C3CD6340122143009aDac0EDa',
        usdValue: bigNumberify(7500),
        asset: 'eip155:1/erc20:0x6a091a3406E0073C3CD6340122143009aDac0EDa',
        premiumOnly: true,
        type: 'token',
        lpType: 'SUSHISWAP',
        id: 3
      },
      {
        address: '0x7858E59e0C01EA06Df3aF3D20aC7B0003275D4Bf',
        assets: [
          {
            asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(30000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        totalSupply: null,
        userBalance: {
          amount: bigNumberify(20),
          usdValue: bigNumberify(5000)
        },
        priceRange: [bigNumberify(0.999), bigNumberify(1)],
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_302285',
        usdValue: bigNumberify(5000),
        asset: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_302285',
        premiumOnly: true,
        type: 'nft',
        lpType: 'UNISWAP_V3',
        id: 4
      },
      {
        address: '0x840DEEef2f115Cf50DA625F7368C24af6fE74410',
        assets: [
          {
            asset: 'eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(2000)
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(30000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2500)
            },
            usdPrice: bigNumberify(2500)
          }
        ],
        totalSupply: null,
        userBalance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(4500)
        },
        priceRange: [bigNumberify(1.03), bigNumberify(1.04)],
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_319213',
        usdValue: bigNumberify(4500),
        asset: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_319213',
        premiumOnly: true,
        type: 'nft',
        lpType: 'UNISWAP_V3',
        id: 5
      },
      {
        account: '0x069D2a5d415894b74C80650A5D67f09E28282B9d',
        userBalance: {
          amount: bigNumberify(450),
          usdValue: bigNumberify(4500)
        },
        totalSupply: bigNumberify(20000),
        assets: [
          {
            asset: 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(2000)
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2500)
            },
            usdPrice: bigNumberify(2500)
          }
        ],
        address: '0xd3d2E2692501A5c9Ca623199D38826e513033a17',
        usdValue: bigNumberify(4500),
        asset: 'eip155:1/erc20:0xd3d2E2692501A5c9Ca623199D38826e513033a17',
        premiumOnly: false,
        type: 'token',
        lpType: 'UNISWAP_V2',
        id: 6
      },
      {
        address: '0x3416cF6C708Da44DB2624D63ea0AAef7113527C6',
        assets: [
          {
            asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(30000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1500)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        totalSupply: null,
        userBalance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(2500)
        },
        priceRange: [bigNumberify(1), bigNumberify(1.0001)],
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_294737',
        usdValue: bigNumberify(2500),
        asset: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_294737',
        premiumOnly: true,
        type: 'nft',
        lpType: 'UNISWAP_V3',
        id: 7
      }
    ];

    const actualResult = get(lpAggregatedBalances());

    expect(actualResult).toMatchObject(expectedResult);
  });
});
