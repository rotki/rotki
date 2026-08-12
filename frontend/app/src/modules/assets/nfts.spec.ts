import { describe, expect, it } from 'vitest';
import { NftResponse } from '@/modules/assets/nfts';

function response(collection: unknown): unknown {
  return {
    addresses: {
      '0xabc': [{
        backgroundColor: null,
        collection,
        externalLink: null,
        imageUrl: null,
        name: 'An NFT',
        permalink: null,
        price: '1.5',
        priceAsset: 'ETH',
        priceInAsset: '1.5',
        tokenIdentifier: '_nft_0xabc_1',
      }],
    },
    entriesFound: 1,
    entriesLimit: 100,
  };
}

describe('nftResponse', () => {
  // The backend sends null here for an NFT that belongs to no collection, which
  // used to fail the parse for the whole page of results rather than that entry.
  it('should parse an nft with no collection', () => {
    const result = NftResponse.safeParse(response(null));

    expect(result.success).toBe(true);
    expect(result.data?.addresses['0xabc'][0].collection).toBeNull();
  });

  it('should parse an nft that has a collection', () => {
    const result = NftResponse.safeParse(response({
      bannerImage: null,
      description: 'A description',
      largeImage: null,
      name: 'Punks',
    }));

    expect(result.success).toBe(true);
    expect(result.data?.addresses['0xabc'][0].collection?.name).toBe('Punks');
  });

  it('should still reject a malformed collection', () => {
    const result = NftResponse.safeParse(response({ name: 42 }));

    expect(result.success).toBe(false);
  });
});
