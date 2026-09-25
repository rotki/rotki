import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { bigNumberify } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { groupByCollection } from './collections';

type CollectionContext = Pick<AggregationContext, 'collectionOf' | 'mainAssetOf' | 'priceOf'>;

function inCollection(members: string[], mainAsset: string | undefined, price: number = 100): CollectionContext {
  return {
    collectionOf: (asset: string): string | undefined => (members.includes(asset) ? 'collection-1' : undefined),
    mainAssetOf: (): string | undefined => mainAsset,
    priceOf: () => bigNumberify(price),
  };
}

describe('groupByCollection', () => {
  it('should use real asset identifier when only one chain has balance', () => {
    const solanaToken = 'solana/token:cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij';
    const mainAsset = 'eip155:1/erc20:0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf';
    const merged: AssetBalanceEntries = {
      [solanaToken]: {
        address: { ...createTestBalance(1, 100), chains: { solana: createTestBalance(1, 100) } },
      },
    };

    const result = groupByCollection(merged, inCollection([solanaToken, mainAsset], mainAsset));

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe(solanaToken);
    expect(result[0].amount.toString()).toBe('1');
    expect(result[0].value.toString()).toBe('100');
    expect(result[0].breakdown).toBeUndefined();
  });

  it('should keep collection main asset for same-chain variants', () => {
    const merged: AssetBalanceEntries = {
      WETH: { uniswap: createTestBalance(10, 40000) },
    };

    const result = groupByCollection(merged, inCollection(['WETH', 'ETH'], 'ETH', 4000));

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe('ETH');
    expect(result[0].breakdown?.map(row => row.asset)).toEqual(['WETH']);
  });

  it('should use collection main asset when multiple chains have balance', () => {
    const solanaToken = 'solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
    const mainAsset = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
    const merged: AssetBalanceEntries = {
      [solanaToken]: {
        address: { ...createTestBalance(90, 90), chains: { solana: createTestBalance(90, 90) } },
      },
      [mainAsset]: {
        address: { ...createTestBalance(10, 10), chains: { eth: createTestBalance(10, 10) } },
      },
    };

    const result = groupByCollection(merged, inCollection([solanaToken, mainAsset], mainAsset));

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe(mainAsset);
    expect(result[0].amount.toString()).toBe('100');
    expect(result[0].value.toString()).toBe('100');
    expect(result[0].breakdown?.map(row => row.asset)).toEqual([solanaToken, mainAsset]);
  });

  it('should show a lone main asset as an ordinary row with no breakdown', () => {
    const merged: AssetBalanceEntries = { USDC: { kraken: createTestBalance(5, 5) } };

    const result = groupByCollection(merged, inCollection(['USDC', 'eip155:10/erc20:0xusdc'], 'USDC'));

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe('USDC');
    expect(result[0].breakdown).toBeUndefined();
  });

  it('should leave assets outside any collection as their own rows', () => {
    const merged: AssetBalanceEntries = {
      BTC: { kraken: createTestBalance(1, 10) },
      DAI: { kraken: createTestBalance(2, 2) },
    };

    const result = groupByCollection(merged, inCollection([], undefined));

    expect(result.map(row => row.asset).sort()).toEqual(['BTC', 'DAI']);
  });

  it('should give a native token a breakdown of its own', () => {
    const merged: AssetBalanceEntries = { ETH: { address: createTestBalance(1, 10) } };

    const result = groupByCollection(merged, inCollection([], undefined));

    expect(result[0].breakdown?.map(row => row.asset)).toEqual(['ETH']);
  });
});
