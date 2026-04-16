import type { AssetProtocolBalancesWithChains } from '@/modules/balances/balance-transformations';
import type { AssetProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import { Zero } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it, vi } from 'vitest';
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
    // Assert that address protocol has chains property
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
    // Assert that address protocol has chains property
    expect(addressProtocol.chains).toBeDefined();
    expect(addressProtocol.chains!.eth).toBeDefined();
    expect(addressProtocol.chains!.eth.amount.toString()).toBe('1');
    expect(addressProtocol.chains!.polygon).toBeDefined();
    expect(addressProtocol.chains!.polygon.amount.toString()).toBe('2');
  });
});
