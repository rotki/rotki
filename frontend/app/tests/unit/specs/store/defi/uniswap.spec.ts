import { beforeAll, describe, expect, it } from 'vitest';
import { useUniswapStore } from '@/store/defi/uniswap';
import type { XswapBalance, XswapPool } from '@rotki/common';

export function setUniswapV2Balances() {
  const { v2Balances } = storeToRefs(useUniswapStore());
  set(v2Balances, {
    '0x069D2a5d415894b74C80650A5D67f09E28282B9d': [
      {
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
        assets: [
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1500),
            },
            usdPrice: bigNumberify(1500),
          },
        ],
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(2500),
        },
      },
      {
        address: '0xd3d2E2692501A5c9Ca623199D38826e513033a17',
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
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(450),
          usdValue: bigNumberify(4500),
        },
      },
    ],
    '0xAEE99Df1f10f9525BcA4fE220029713b0EaCE215': [
      {
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
        assets: [
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000),
            },
            usdPrice: bigNumberify(1500),
          },
        ],
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(600),
          usdValue: bigNumberify(6000),
        },
      },
    ],
  });
}

describe('uniswap:v2', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
    setUniswapV2Balances();
  });

  it('aggregatedBalances', () => {
    const store = useUniswapStore();
    const { uniswapV2Balances } = store;

    const expectedResult: XswapBalance[] = [
      {
        account: '0x069D2a5d415894b74C80650A5D67f09E28282B9d',
        userBalance: {
          amount: bigNumberify(1600),
          usdValue: bigNumberify(8500),
        },
        totalSupply: bigNumberify(20000),
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
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
      },
      {
        account: '0x069D2a5d415894b74C80650A5D67f09E28282B9d',
        userBalance: {
          amount: bigNumberify(450),
          usdValue: bigNumberify(4500),
        },
        totalSupply: bigNumberify(20000),
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
        address: '0xd3d2E2692501A5c9Ca623199D38826e513033a17',
      },
    ];

    const actualResult = get(uniswapV2Balances([]));

    expect(actualResult).toMatchObject(expectedResult);
  });

  it('filter balances by address', () => {
    const store = useUniswapStore();
    const { uniswapV2Balances } = store;

    const expectedResult: XswapBalance[] = [
      {
        account: '0xAEE99Df1f10f9525BcA4fE220029713b0EaCE215',
        userBalance: {
          amount: bigNumberify(600),
          usdValue: bigNumberify(6000),
        },
        totalSupply: bigNumberify(20000),
        assets: [
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000),
            },
            usdPrice: bigNumberify(1000),
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000),
            },
            usdPrice: bigNumberify(1500),
          },
        ],
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
      },
    ];

    const actualResult = get(uniswapV2Balances(['0xAEE99Df1f10f9525BcA4fE220029713b0EaCE215']));

    expect(actualResult).toMatchObject(expectedResult);
  });

  it('addresses', () => {
    const store = useUniswapStore();
    const { uniswapV2Addresses } = storeToRefs(store);

    const expectedResult: string[] = [
      '0x069D2a5d415894b74C80650A5D67f09E28282B9d',
      '0xAEE99Df1f10f9525BcA4fE220029713b0EaCE215',
    ];

    const actualResult = get(uniswapV2Addresses);

    expect(actualResult).toMatchObject(expectedResult);
  });

  it('pools', () => {
    const store = useUniswapStore();
    const { uniswapV2PoolAssets } = storeToRefs(store);

    const expectedResult: XswapPool[] = [
      {
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
        assets: [
          'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
          'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
        ],
      },
      {
        address: '0xd3d2E2692501A5c9Ca623199D38826e513033a17',
        assets: [
          'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
          'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        ],
      },
    ];

    const actualResult = get(uniswapV2PoolAssets);

    expect(actualResult).toMatchObject(expectedResult);
  });
});
