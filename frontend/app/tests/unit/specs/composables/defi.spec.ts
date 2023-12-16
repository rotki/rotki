import { LpType } from '@rotki/common/lib/defi';
import { setBalancerBalances } from '../store/defi/balancer.spec';
import { setSushiswapBalances } from '../store/defi/sushiswap.spec';
import { setUniswapV2Balances, setUniswapV3Balances } from '../store/defi/uniswap.spec';
import type { XSwapLiquidityBalance } from '@rotki/common/lib/defi/xswap';

describe('composables::defi', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
    setUniswapV2Balances();
    setUniswapV3Balances();
    setSushiswapBalances();
    setBalancerBalances();
  });

  it('lpAggregatedBalances', () => {
    const { lpAggregatedBalances } = useLiquidityPosition();

    const expectedResult: XSwapLiquidityBalance[] = [
      {
        usdValue: bigNumberify(12000),
        asset: 'eip155:1/erc20:0x49ff149D649769033d43783E7456F626862CD160',
        premiumOnly: true,
        assets: [
          {
            asset: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0x408e41876cCCDC0F92210600ef50372656052a38',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(6000),
            },
            usdPrice: bigNumberify(2000),
          },
          {
            asset: 'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000),
            },
            usdPrice: bigNumberify(1000),
          },
        ],
        type: 'token',
        lpType: LpType.BALANCER,
        id: 0,
      },
      {
        usdValue: bigNumberify(10000),
        asset: 'eip155:1/erc20:0xc409D34aCcb279620B1acDc05E408e287d543d17',
        premiumOnly: true,
        assets: [
          {
            asset: 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(4500),
            },
            usdPrice: bigNumberify(4500),
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000),
            },
            usdPrice: bigNumberify(2000),
          },
          {
            asset: 'eip155:1/erc20:0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(3500),
            },
            usdPrice: bigNumberify(3500),
          },
        ],
        type: 'token',
        lpType: LpType.BALANCER,
        id: 1,
      },
      {
        assets: [
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(4500),
            },
            usdPrice: bigNumberify(1500),
          },
        ],
        usdValue: bigNumberify(8500),
        asset: 'eip155:1/erc20:0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
        premiumOnly: false,
        type: 'token',
        lpType: LpType.UNISWAP_V2,
        id: 2,
      },
      {
        assets: [
          {
            asset: 'eip155:1/erc20:0x767FE9EDC9E0dF98E07454847909b5E959D7ca0E',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(3000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(3),
              usdValue: bigNumberify(4500),
            },
            usdPrice: bigNumberify(1500),
          },
        ],
        usdValue: bigNumberify(7500),
        asset: 'eip155:1/erc20:0x6a091a3406E0073C3CD6340122143009aDac0EDa',
        premiumOnly: true,
        type: 'token',
        lpType: LpType.SUSHISWAP,
        id: 3,
      },
      {
        assets: [
          {
            asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(30000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000),
            },
            usdPrice: bigNumberify(1500),
          },
        ],
        usdValue: bigNumberify(5000),
        asset: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_302285',
        premiumOnly: true,
        type: 'nft',
        lpType: LpType.UNISWAP_V3,
        id: 4,
      },
      {
        assets: [
          {
            asset: 'eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000),
            },
            usdPrice: bigNumberify(2000),
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(30000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2500),
            },
            usdPrice: bigNumberify(2500),
          },
        ],
        usdValue: bigNumberify(4500),
        asset: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_319213',
        premiumOnly: true,
        type: 'nft',
        lpType: LpType.UNISWAP_V3,
        id: 5,
      },
      {
        assets: [
          {
            asset: 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2000),
            },
            usdPrice: bigNumberify(2000),
          },
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(2500),
            },
            usdPrice: bigNumberify(2500),
          },
        ],
        usdValue: bigNumberify(4500),
        asset: 'eip155:1/erc20:0xd3d2E2692501A5c9Ca623199D38826e513033a17',
        premiumOnly: false,
        type: 'token',
        lpType: LpType.UNISWAP_V2,
        id: 6,
      },
      {
        assets: [
          {
            asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            totalAmount: bigNumberify(20000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(30000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1500),
            },
            usdPrice: bigNumberify(1500),
          },
        ],
        usdValue: bigNumberify(2500),
        asset: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_294737',
        premiumOnly: true,
        type: 'nft',
        lpType: LpType.UNISWAP_V3,
        id: 7,
      },
    ];

    const actualResult = get(lpAggregatedBalances());

    expect(actualResult).toMatchObject(expectedResult);
  });
});
