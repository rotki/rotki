import { XswapBalance, XswapPool } from '@rotki/common/lib/defi/xswap';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { useUniswapStore } from '@/store/defi/uniswap';
import { bigNumberify } from '@/utils/bignumbers';

export const setUniswapV2Balances = () => {
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
              usdValue: bigNumberify(1000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(1),
              usdValue: bigNumberify(1500)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(1000),
          usdValue: bigNumberify(2500)
        }
      },
      {
        address: '0xd3d2E2692501A5c9Ca623199D38826e513033a17',
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
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(450),
          usdValue: bigNumberify(4500)
        }
      }
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
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        totalSupply: bigNumberify(20000),
        userBalance: {
          amount: bigNumberify(600),
          usdValue: bigNumberify(6000)
        }
      }
    ]
  });
};

export const setUniswapV3Balances = () => {
  const { v3Balances } = storeToRefs(useUniswapStore());
  set(v3Balances, {
    '0x42a49DcF7902C6B7938A00Cdbe62a112A2b539E8': [
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
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_294737'
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
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_302285'
      }
    ],
    '0xa7c43e2057D89B6946b8865EfC8BEe3a4eA7d28D': [
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
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_319213'
      }
    ]
  });
};

describe('uniswap:v2', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
    setUniswapV2Balances();
  });

  test('aggregatedBalances', () => {
    const store = useUniswapStore();
    const { uniswapV2Balances } = store;

    const expectedResult: XswapBalance[] = [
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
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'
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
        address: '0xd3d2E2692501A5c9Ca623199D38826e513033a17'
      }
    ];

    const actualResult = get(uniswapV2Balances([]));

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('filter balances by address', () => {
    const store = useUniswapStore();
    const { uniswapV2Balances } = store;

    const expectedResult: XswapBalance[] = [
      {
        account: '0xAEE99Df1f10f9525BcA4fE220029713b0EaCE215',
        userBalance: {
          amount: bigNumberify(600),
          usdValue: bigNumberify(6000)
        },
        totalSupply: bigNumberify(20000),
        assets: [
          {
            asset: 'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(2000)
            },
            usdPrice: bigNumberify(1000)
          },
          {
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
            totalAmount: bigNumberify(10000),
            userBalance: {
              amount: bigNumberify(2),
              usdValue: bigNumberify(3000)
            },
            usdPrice: bigNumberify(1500)
          }
        ],
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'
      }
    ];

    const actualResult = get(
      uniswapV2Balances(['0xAEE99Df1f10f9525BcA4fE220029713b0EaCE215'])
    );

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('addresses', () => {
    const store = useUniswapStore();
    const { uniswapV2Addresses } = storeToRefs(store);

    const expectedResult: string[] = [
      '0x069D2a5d415894b74C80650A5D67f09E28282B9d',
      '0xAEE99Df1f10f9525BcA4fE220029713b0EaCE215'
    ];

    const actualResult = get(uniswapV2Addresses);

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('pools', () => {
    const store = useUniswapStore();
    const { uniswapV2PoolAssets } = storeToRefs(store);

    const expectedResult: XswapPool[] = [
      {
        address: '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852',
        assets: [
          'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
          'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'
        ]
      },
      {
        address: '0xd3d2E2692501A5c9Ca623199D38826e513033a17',
        assets: [
          'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
          'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
        ]
      }
    ];

    const actualResult = get(uniswapV2PoolAssets);

    expect(actualResult).toMatchObject(expectedResult);
  });
});

describe('uniswap:v3', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
    setUniswapV3Balances();
  });

  test('aggregatedBalances', () => {
    const store = useUniswapStore();
    const { uniswapV3Balances } = store;

    const expectedResult: XswapBalance[] = [
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
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_294737'
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
        userBalance: {
          amount: bigNumberify(20),
          usdValue: bigNumberify(5000)
        },
        priceRange: [bigNumberify(0.999), bigNumberify(1)],
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_302285'
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
        userBalance: {
          amount: bigNumberify(10),
          usdValue: bigNumberify(4500)
        },
        priceRange: [bigNumberify(1.03), bigNumberify(1.04)],
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_319213'
      }
    ];

    const actualResult = get(uniswapV3Balances([]));

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('filter balances by address', () => {
    const store = useUniswapStore();
    const { uniswapV3Balances } = store;

    const expectedResult: XswapBalance[] = [
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
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_294737'
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
        nftId: '_nft_0xc36442b4a4522e871399cd717abdd847ab11fe88_302285'
      }
    ];

    const actualResult = get(
      uniswapV3Balances(['0x42a49DcF7902C6B7938A00Cdbe62a112A2b539E8'])
    );

    expect(actualResult).toMatchObject(expectedResult);
  });

  test('pools', () => {
    const store = useUniswapStore();
    const { uniswapV3PoolAssets } = storeToRefs(store);

    const expectedResult: XswapPool[] = [
      {
        address: '0x3416cF6C708Da44DB2624D63ea0AAef7113527C6',
        assets: [
          'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
          'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'
        ]
      },
      {
        address: '0x7858E59e0C01EA06Df3aF3D20aC7B0003275D4Bf',
        assets: [
          'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
          'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'
        ]
      },
      {
        address: '0x840DEEef2f115Cf50DA625F7368C24af6fE74410',
        assets: [
          'eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704',
          'eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
        ]
      }
    ];

    const actualResult = get(uniswapV3PoolAssets);

    expect(actualResult).toMatchObject(expectedResult);
  });
});
