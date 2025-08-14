import type { Balances } from '@/types/blockchain/accounts';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { blockchainToAssetProtocolBalances } from './balance-transformations';

describe('balance transformations with chains', () => {
  it('should preserve per-chain data for address protocol', () => {
    const mockBalances: Balances = {
      eth: {
        '0x1234': {
          assets: {
            ETH: {
              address: createTestBalance(1, 100),
            },
          },
          liabilities: {},
        },
      },
      polygon: {
        '0x1234': {
          assets: {
            ETH: {
              address: createTestBalance(2, 200),
            },
          },
          liabilities: {},
        },
      },
    };

    const result = blockchainToAssetProtocolBalances(mockBalances);

    expect(result.ETH).toBeDefined();
    expect(result.ETH.address).toBeDefined();

    // Should have aggregated totals
    expect(result.ETH.address.amount.toString()).toBe('3');
    expect(result.ETH.address.usdValue.toString()).toBe('300');

    // Should have per-chain breakdown
    expect(result.ETH.address.chains).toBeDefined();
    expect(result.ETH.address.chains!.eth).toBeDefined();
    expect(result.ETH.address.chains!.polygon).toBeDefined();

    expect(result.ETH.address.chains!.eth.amount.toString()).toBe('1');
    expect(result.ETH.address.chains!.eth.usdValue.toString()).toBe('100');

    expect(result.ETH.address.chains!.polygon.amount.toString()).toBe('2');
    expect(result.ETH.address.chains!.polygon.usdValue.toString()).toBe('200');
  });

  it('should not add chains property for non-address protocols', () => {
    const mockBalances: Balances = {
      eth: {
        '0x1234': {
          assets: {
            ETH: {
              'uniswap-v3': createTestBalance(1, 100),
            },
          },
          liabilities: {},
        },
      },
      polygon: {
        '0x1234': {
          assets: {
            ETH: {
              'uniswap-v3': createTestBalance(2, 200),
            },
          },
          liabilities: {},
        },
      },
    };

    const result = blockchainToAssetProtocolBalances(mockBalances);

    expect(result.ETH).toBeDefined();
    expect(result.ETH['uniswap-v3']).toBeDefined();

    // Should have aggregated totals
    expect(result.ETH['uniswap-v3'].amount.toString()).toBe('3');
    expect(result.ETH['uniswap-v3'].usdValue.toString()).toBe('300');

    // Should NOT have per-chain breakdown for non-address protocols
    expect(result.ETH['uniswap-v3'].chains).toBeUndefined();
  });

  it('should handle single chain with address protocol', () => {
    const mockBalances: Balances = {
      eth: {
        '0x1234': {
          assets: {
            ETH: {
              address: createTestBalance(1, 100),
            },
          },
          liabilities: {},
        },
      },
    };

    const result = blockchainToAssetProtocolBalances(mockBalances);

    expect(result.ETH).toBeDefined();
    expect(result.ETH.address).toBeDefined();

    // Should have the balance values
    expect(result.ETH.address.amount.toString()).toBe('1');
    expect(result.ETH.address.usdValue.toString()).toBe('100');

    // Should have per-chain breakdown even for single chain
    expect(result.ETH.address.chains).toBeDefined();
    expect(result.ETH.address.chains!.eth).toBeDefined();
    expect(result.ETH.address.chains!.eth.amount.toString()).toBe('1');
    expect(result.ETH.address.chains!.eth.usdValue.toString()).toBe('100');
  });
});
