import type { AssetProtocolBalancesWithChains } from '@/composables/balances/balance-transformations';
import type { Balances } from '@/types/blockchain/accounts';
import { Zero } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it, vi } from 'vitest';
import { blockchainToAssetProtocolBalances, processCollectionGrouping } from './balance-transformations';

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
    expect(result.ETH.address.value.toString()).toBe('300');

    // Should have per-chain breakdown
    expect(result.ETH.address.chains).toBeDefined();
    expect(result.ETH.address.chains!.eth).toBeDefined();
    expect(result.ETH.address.chains!.polygon).toBeDefined();

    expect(result.ETH.address.chains!.eth.amount.toString()).toBe('1');
    expect(result.ETH.address.chains!.eth.value.toString()).toBe('100');

    expect(result.ETH.address.chains!.polygon.amount.toString()).toBe('2');
    expect(result.ETH.address.chains!.polygon.value.toString()).toBe('200');
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
    expect(result.ETH['uniswap-v3'].value.toString()).toBe('300');

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
    expect(result.ETH.address.value.toString()).toBe('100');

    // Should have per-chain breakdown even for single chain
    expect(result.ETH.address.chains).toBeDefined();
    expect(result.ETH.address.chains!.eth).toBeDefined();
    expect(result.ETH.address.chains!.eth.amount.toString()).toBe('1');
    expect(result.ETH.address.chains!.eth.value.toString()).toBe('100');
  });
});

describe('processCollectionGrouping', () => {
  it('should use real asset identifier when only one chain has balance', () => {
    const solanaToken = 'solana/token:cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij';
    const mainAsset = 'eip155:1/erc20:0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf';

    const aggregatedBalances: AssetProtocolBalancesWithChains = {
      [solanaToken]: {
        address: {
          ...createTestBalance(1, 100),
          chains: {
            solana: createTestBalance(1, 100),
          },
        },
      },
    };

    const mockCollectionId = vi.fn().mockImplementation((asset: string) => ({
      value: asset === solanaToken || asset === mainAsset ? 'collection-1' : undefined,
    }));

    const mockCollectionMainAsset = vi.fn().mockReturnValue({ value: mainAsset });

    const result = processCollectionGrouping(
      aggregatedBalances,
      mockCollectionId,
      mockCollectionMainAsset,
      () => Zero.plus(100),
      Zero,
    );

    expect(result).toHaveLength(1);
    // Should use the actual solana token identifier, not the ERC20 collection header
    expect(result[0].asset).toBe(solanaToken);
    expect(result[0].amount.toString()).toBe('1');
    expect(result[0].value.toString()).toBe('100');
    // Should not have breakdown since there's only one chain
    expect(result[0].breakdown).toBeUndefined();
  });

  it('should keep collection main asset for same-chain variants', () => {
    const aggregatedBalances: AssetProtocolBalancesWithChains = {
      WETH: {
        uniswap: createTestBalance(10, 40000),
      },
    };

    const mockCollectionId = vi.fn().mockImplementation((asset: string) => ({
      value: asset === 'WETH' || asset === 'ETH' ? 'collection-1' : undefined,
    }));

    const mockCollectionMainAsset = vi.fn().mockReturnValue({ value: 'ETH' });

    const result = processCollectionGrouping(
      aggregatedBalances,
      mockCollectionId,
      mockCollectionMainAsset,
      () => Zero.plus(4000),
      Zero,
    );

    expect(result).toHaveLength(1);
    // Should keep ETH as the collection header (same chain, WETH is a wrapped variant)
    expect(result[0].asset).toBe('ETH');
    expect(result[0].breakdown).toHaveLength(1);
    expect(result[0].breakdown![0].asset).toBe('WETH');
  });

  it('should use collection main asset when multiple chains have balance', () => {
    const solanaToken = 'solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
    const mainAsset = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';

    const aggregatedBalances: AssetProtocolBalancesWithChains = {
      [solanaToken]: {
        address: {
          ...createTestBalance(90, 90),
          chains: {
            solana: createTestBalance(90, 90),
          },
        },
      },
      [mainAsset]: {
        address: {
          ...createTestBalance(10, 10),
          chains: {
            eth: createTestBalance(10, 10),
          },
        },
      },
    };

    const mockCollectionId = vi.fn().mockImplementation((asset: string) => ({
      value: asset === solanaToken || asset === mainAsset ? 'collection-1' : undefined,
    }));

    const mockCollectionMainAsset = vi.fn().mockReturnValue({ value: mainAsset });

    const result = processCollectionGrouping(
      aggregatedBalances,
      mockCollectionId,
      mockCollectionMainAsset,
      () => Zero.plus(100),
      Zero,
    );

    expect(result).toHaveLength(1);
    // Should use the collection main asset when multiple chains have balance
    expect(result[0].asset).toBe(mainAsset);
    expect(result[0].amount.toString()).toBe('100');
    expect(result[0].value.toString()).toBe('100');
    // Should have breakdown with both chain variants
    expect(result[0].breakdown).toBeDefined();
    expect(result[0].breakdown).toHaveLength(2);
  });
});
