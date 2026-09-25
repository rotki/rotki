import type { AssetProtocolBalancesWithChains } from '@/modules/balances/aggregation/core/balance-transformations';
import type { AssetProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import { type AssetBalanceWithPriceAndChains, type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { assert, describe, expect, it, vi } from 'vitest';
import { summarizeAssetProtocols } from './asset-summary';

describe('summarizeAssetProtocols with chains', () => {
  it('should preserve chain data for address protocol', () => {
    const mockSources: Record<string, AssetProtocolBalances | AssetProtocolBalancesWithChains> = {
      blockchain: {
        ETH: {
          address: {
            ...createTestBalance(3, 300),
            chains: {
              eth: createTestBalance(1, 100),
              polygon: createTestBalance(2, 200),
            },
          },
        },
      },
    };

    const result = summarizeAssetProtocols(
      {
        resolveIdentifier: (id: string): string => id,
        sources: mockSources,
      },
      {
        hideIgnored: false,
        isAssetIgnored: () => false,
      },
      {
        getAssetPrice: () => Zero.plus(100),
        noPrice: Zero,
      },
      {
        groupCollections: false,
      },
    );

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe('ETH');
    expect(result[0].amount.toString()).toBe('3');
    expect(result[0].value.toString()).toBe('300');

    // Check that chains data is preserved in perProtocol array
    expect(result[0].perProtocol).toBeDefined();
    const addressProtocol = result[0].perProtocol!.find(p => p.protocol === 'address')!;
    expect(addressProtocol).toBeDefined();
    expect(addressProtocol.chains).toBeDefined();
    expect(addressProtocol.chains!.eth).toBeDefined();
    expect(addressProtocol.chains!.eth.amount.toString()).toBe('1');
    expect(addressProtocol.chains!.eth.value.toString()).toBe('100');
    expect(addressProtocol.chains!.polygon).toBeDefined();
    expect(addressProtocol.chains!.polygon.amount.toString()).toBe('2');
    expect(addressProtocol.chains!.polygon.value.toString()).toBe('200');
  });

  it('should not have chains property for non-address protocols', () => {
    const mockSources: Record<string, AssetProtocolBalances> = {
      blockchain: {
        ETH: {
          'uniswap-v3': createTestBalance(3, 300),
        },
      },
    };

    const result = summarizeAssetProtocols(
      {
        resolveIdentifier: (id: string): string => id,
        sources: mockSources,
      },
      {
        hideIgnored: false,
        isAssetIgnored: () => false,
      },
      {
        getAssetPrice: () => Zero.plus(100),
        noPrice: Zero,
      },
      {
        groupCollections: false,
      },
    );

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe('ETH');
    expect(result[0].amount.toString()).toBe('3');
    expect(result[0].value.toString()).toBe('300');
    // Check that chains data is not present for non-address protocols
    expect(result[0].perProtocol).toBeDefined();
    const uniswapProtocol = result[0].perProtocol!.find(p => p.protocol === 'uniswap-v3')!;
    expect(uniswapProtocol).toBeDefined();

    // Assert that non-address protocol doesn't have chains
    expect(uniswapProtocol.chains).toBeUndefined();
  });

  it('should aggregate chains data when grouping collections', () => {
    const mockSources: Record<string, AssetProtocolBalances | AssetProtocolBalancesWithChains> = {
      blockchain: {
        'asset-1': {
          address: {
            ...createTestBalance(1, 100),

            chains: {
              eth: createTestBalance(1, 100),
            },
          },
        },
        'asset-2': {
          address: {
            ...createTestBalance(2, 200),
            chains: {
              polygon: createTestBalance(2, 200),
            },
          },
        },
      },
    };

    const mockCollectionId = vi.fn().mockImplementation((asset: string): string | undefined =>
      asset === 'asset-1' || asset === 'asset-2' ? 'collection-1' : undefined,
    );

    const mockCollectionMainAsset = vi.fn().mockReturnValue('asset-1');

    const result = summarizeAssetProtocols(
      {
        resolveIdentifier: (id: string): string => id,
        sources: mockSources,
      },
      {
        hideIgnored: false,
        isAssetIgnored: () => false,
      },
      {
        getAssetPrice: () => Zero.plus(100),
        noPrice: Zero,
      },
      {
        groupCollections: true,
        getCollectionId: mockCollectionId,
        getCollectionMainAsset: mockCollectionMainAsset,
      },
    );

    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe('asset-1');
    expect(result[0].amount.toString()).toBe('3');
    expect(result[0].value.toString()).toBe('300');

    // Check that chains data is aggregated in perProtocol array
    expect(result[0].perProtocol).toBeDefined();
    const addressProtocol = result[0].perProtocol!.find(p => p.protocol === 'address')!;
    expect(addressProtocol).toBeDefined();
    expect(addressProtocol.chains).toBeDefined();
    expect(addressProtocol.chains!.eth).toBeDefined();
    expect(addressProtocol.chains!.eth.amount.toString()).toBe('1');
    expect(addressProtocol.chains!.polygon).toBeDefined();
    expect(addressProtocol.chains!.polygon.amount.toString()).toBe('2');
  });
});

describe('summarizeAssetProtocols invariants', () => {
  type Sources = Record<string, AssetProtocolBalances | AssetProtocolBalancesWithChains>;

  const collections: Record<string, { members: string[]; main: string | undefined }> = {
    stable: { main: 'USDC', members: ['USDC', 'eip155:10/erc20:0xusdc', 'eip155:137/erc20:0xusdc'] },
  };

  function summarize(sources: Sources, groupCollections: boolean = true): AssetBalanceWithPriceAndChains[] {
    return summarizeAssetProtocols(
      { resolveIdentifier: (id: string): string => id, sources },
      { hideIgnored: true, isAssetIgnored: (id: string): boolean => id === 'SPAM' },
      { getAssetPrice: (): BigNumber => bigNumberify(1), noPrice: Zero },
      groupCollections
        ? {
            getCollectionId: (asset: string): string | undefined =>
              Object.keys(collections).find(id => collections[id].members.includes(asset)),
            getCollectionMainAsset: (id: string): string | undefined => collections[id]?.main,
            groupCollections: true,
          }
        : { groupCollections: false },
    );
  }

  /** BigNumbers built along different paths can differ internally while holding the same value. */
  function plain(rows: AssetBalanceWithPriceAndChains[]): unknown {
    return JSON.parse(JSON.stringify(rows));
  }

  function reversed(sources: Sources): Sources {
    return Object.fromEntries(Object.entries(sources).reverse().map(([source, assets]) => [
      source,
      Object.fromEntries(Object.entries(assets).reverse()),
    ]));
  }

  function grandTotal(rows: AssetBalanceWithPriceAndChains[]): string {
    return rows.reduce((total, row) => total.plus(row.value), Zero).toFixed();
  }

  const sources: Sources = {
    blockchain: {
      'ETH': {
        address: { ...createTestBalance(1, 3000), chains: { eth: createTestBalance(1, 3000) } },
        aave: createTestBalance(2, 6000),
      },
      'SPAM': { address: { ...createTestBalance(9, 9), chains: { eth: createTestBalance(9, 9) } } },
      'eip155:10/erc20:0xusdc': {
        address: { ...createTestBalance(10, 10), chains: { optimism: createTestBalance(10, 10) } },
      },
      'eip155:137/erc20:0xusdc': {
        address: { ...createTestBalance(20, 20), chains: { polygon: createTestBalance(20, 20) } },
      },
    },
    exchanges: {
      'BTC': { kraken: createTestBalance(1, 50000) },
      'eip155:10/erc20:0xusdc': { kraken: createTestBalance(5, 5) },
    },
    manual: {
      BTC: { kraken: createTestBalance(1, 50000) },
      USDC: { kraken: createTestBalance(7, 7) },
    },
  };

  it('should produce the same rows whichever order the sources and assets arrive in', () => {
    expect(plain(summarize(reversed(sources)))).toEqual(plain(summarize(sources)));
    expect(plain(summarize(reversed(sources), false))).toEqual(plain(summarize(sources, false)));
  });

  it('should list rows by value, highest first, with or without collection grouping', () => {
    for (const groupCollections of [true, false]) {
      const values = summarize(sources, groupCollections).map(row => row.value.toNumber());
      expect(values).toEqual([...values].sort((a, b) => b - a));
    }
  });

  it('should keep the grand total when collections are grouped', () => {
    expect(grandTotal(summarize(sources))).toBe(grandTotal(summarize(sources, false)));
  });

  it('should mark a merged collection protocol as manual whichever member holds the manual balance', () => {
    for (const ordered of [sources, reversed(sources)]) {
      const stable = summarize(ordered).find(row => row.asset === 'USDC');
      const kraken = stable?.perProtocol?.find(protocol => protocol.protocol === 'kraken');
      expect(kraken?.containsManual).toBe(true);
      expect(kraken?.amount.toFixed()).toBe('12');
    }
  });

  it('should keep every chain of a merged address protocol whichever member arrives first', () => {
    for (const ordered of [sources, reversed(sources)]) {
      const stable = summarize(ordered).find(row => row.asset === 'USDC');
      const address = stable?.perProtocol?.find(protocol => protocol.protocol === 'address');
      assert(address && 'chains' in address && address.chains);
      expect(Object.keys(address.chains).sort()).toEqual(['optimism', 'polygon']);
    }
  });

  it('should list the members of a collection separately when its main asset is unknown', () => {
    collections.stable.main = undefined;
    try {
      const rows = summarize(sources);
      expect(rows.map(row => row.asset)).toEqual(expect.arrayContaining([
        'USDC',
        'eip155:10/erc20:0xusdc',
        'eip155:137/erc20:0xusdc',
      ]));
      expect(grandTotal(rows)).toBe(grandTotal(summarize(sources, false)));
    }
    finally {
      collections.stable.main = 'USDC';
    }
  });
});
