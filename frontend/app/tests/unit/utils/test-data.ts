import type { BlockchainAccount } from '@/types/blockchain/accounts';
import type { BlockchainBalances } from '@/types/blockchain/balances';
import type { ExchangeData } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { BalanceType } from '@/types/balances';

export const testManualBalances: ManualBalanceWithValue[] = [{
  amount: bigNumberify(500),
  asset: 'aUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 1,
  label: 'test 1',
  location: 'external',
  tags: [],
  usdValue: bigNumberify(500),
  value: bigNumberify(500),
}, {
  amount: bigNumberify(500),
  asset: 'bUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 2,
  label: 'test 2',
  location: 'external',
  tags: [],
  usdValue: bigNumberify(500),
  value: bigNumberify(500),
}, {
  amount: bigNumberify(1000),
  asset: 'GNO',
  balanceType: BalanceType.ASSET,
  identifier: 3,
  label: 'test 3',
  location: 'kraken',
  tags: [],
  usdValue: bigNumberify(1000),
  value: bigNumberify(1000),
}, {
  amount: bigNumberify(500),
  asset: 'aUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 4,
  label: 'test 4',
  location: 'kraken',
  tags: [],
  usdValue: bigNumberify(500),
  value: bigNumberify(500),
}, {
  amount: bigNumberify(500),
  asset: 'bUSDC',
  balanceType: BalanceType.ASSET,
  identifier: 5,
  label: 'test 5',
  location: 'kraken',
  tags: [],
  usdValue: bigNumberify(500),
  value: bigNumberify(500),
}];

export const testExchangeBalances: ExchangeData = {
  kraken: {
    aUSDC: {
      amount: bigNumberify(2000),
      usdValue: bigNumberify(2000),
      value: bigNumberify(2000),
    },
    cUSDC: {
      amount: bigNumberify(1000),
      usdValue: bigNumberify(1000),
      value: bigNumberify(1000),
    },
    GNO: {
      amount: bigNumberify(1000),
      usdValue: bigNumberify(1000),
      value: bigNumberify(1000),
    },
  },
};

export const testEthereumBalances: BlockchainBalances = {
  perAccount: {
    eth: {
      '0xaddress1': {
        assets: {
          aUSDC: {
            address: {
              amount: bigNumberify(400),
              usdValue: bigNumberify(400),
              value: bigNumberify(400),
            },
          },
          cUSDC: {
            address: {
              amount: bigNumberify(300),
              usdValue: bigNumberify(300),
              value: bigNumberify(300),
            },
          },
          GNO: {
            address: {
              amount: bigNumberify(300),
              usdValue: bigNumberify(300),
              value: bigNumberify(300),
            },
          },

        },
        liabilities: {},
      },
      '0xaddress2': {
        assets: {
          aUSDC: {
            address: {
              amount: bigNumberify(800),
              usdValue: bigNumberify(800),
              value: bigNumberify(800),
            },
          },
          cUSDC: {
            address: {
              amount: bigNumberify(800),
              usdValue: bigNumberify(800),
              value: bigNumberify(800),
            },
          },
          GNO: {
            address: {
              amount: bigNumberify(400),
              usdValue: bigNumberify(400),
              value: bigNumberify(400),
            },
          },
        },
        liabilities: {},
      },
    },
  },
  totals: {
    assets: {},
    liabilities: {},
  },
};

export const testAccounts: BlockchainAccount[] = [{
  chain: 'eth',
  data: {
    address: '0xaddress1',
    type: 'address',
  },
  nativeAsset: 'ETH',
}, {
  chain: 'eth',
  data: {
    address: '0xaddress2',
    type: 'address',
  },
  nativeAsset: 'ETH',
}];

export function createMockExchangeBalances(): ExchangeData {
  return {
    coinbase: {
      ETH: createTestBalance(2000, 2000),
      ETH2: createTestBalance(2000, 2000),
    },
    kraken: {
      ETH: createTestBalance(1000, 1000),
      ETH2: createTestBalance(1000, 1000),
    },
  };
}
