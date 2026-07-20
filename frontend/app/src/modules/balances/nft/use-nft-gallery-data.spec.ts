import type { Nft } from '@/modules/assets/nfts';
import type { NftPrice } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useNftGalleryData } from './use-nft-gallery-data';

const { spies } = vi.hoisted(() => ({
  spies: {
    fetchNfts: vi.fn(),
    fetchNftsPrices: vi.fn(),
  },
}));

vi.mock('@/modules/assets/use-asset-nft', () => ({
  useNfts: (): object => ({ fetchNfts: spies.fetchNfts }),
}));
vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): object => ({ fetchNftsPrices: spies.fetchNftsPrices }),
}));

// these nfts are spread (`{ ...nft }`) by the composable, so they must be real objects.
function nft(tokenIdentifier: string): Nft {
  return {
    backgroundColor: null,
    collection: { bannerImage: null, description: null, largeImage: null, name: 'Collection' },
    externalLink: undefined,
    imageUrl: null,
    name: tokenIdentifier,
    permalink: null,
    price: bigNumberify(1),
    priceAsset: 'USD',
    priceInAsset: bigNumberify(1),
    tokenIdentifier,
  };
}

describe('useNftGalleryData', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should store the fetched nfts and stop loading', async () => {
    spies.fetchNfts.mockResolvedValue({ result: { addresses: { '0x1': [] }, entriesFound: 3, entriesLimit: 10 } });
    const data = useNftGalleryData();
    await data.fetchNfts();
    expect(get(data.total)).toBe(3);
    expect(get(data.limit)).toBe(10);
    expect(get(data.perAccount)).toEqual({ '0x1': [] });
    expect(get(data.loading)).toBe(false);
  });

  it('should record the error message on a failed fetch', async () => {
    spies.fetchNfts.mockResolvedValue({ message: 'entries limit reached' });
    const data = useNftGalleryData();
    await data.fetchNfts();
    expect(get(data.error)).toBe('entries limit reached');
    expect(get(data.nftLimited)).toBe(true);
  });

  it('should flatten per-account nfts and attach the address', async () => {
    spies.fetchNfts.mockResolvedValue({
      result: { addresses: { '0xabc': [nft('t1'), nft('t2')] }, entriesFound: 2, entriesLimit: 10 },
    });
    const data = useNftGalleryData();
    await data.fetchNfts();
    const nfts = get(data.nfts);
    expect(nfts).toHaveLength(2);
    expect(nfts[0]).toMatchObject({ address: '0xabc', tokenIdentifier: 't1' });
  });

  it('should apply a manually-entered price to the matching nft', async () => {
    spies.fetchNftsPrices.mockResolvedValue([
      createMock<NftPrice>({
        asset: 't1',
        manuallyInput: true,
        price: bigNumberify(5),
        priceAsset: 'ETH',
        priceInAsset: bigNumberify(2),
      }),
    ]);
    spies.fetchNfts.mockResolvedValue({
      result: { addresses: { '0xabc': [nft('t1')] }, entriesFound: 1, entriesLimit: 10 },
    });
    const data = useNftGalleryData();
    await data.fetchNfts();
    await data.fetchPrices();
    const nfts = get(data.nfts);
    expect(nfts[0]).toMatchObject({ price: bigNumberify(5), priceAsset: 'ETH' });
  });

  it('should key fetched prices by asset', async () => {
    spies.fetchNftsPrices.mockResolvedValue([createMock<NftPrice>({ asset: 't1' })]);
    const data = useNftGalleryData();
    await data.fetchPrices();
    expect(get(data.prices)).toHaveProperty('t1');
  });

  it('should capture a price fetch error', async () => {
    spies.fetchNftsPrices.mockRejectedValue(new Error('price boom'));
    const data = useNftGalleryData();
    await data.fetchPrices();
    expect(get(data.priceError)).toBe('price boom');
  });
});
