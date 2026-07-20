import type { ComputedRef } from 'vue';
import type { GalleryNft } from '@/modules/assets/nfts';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNftGalleryLayout } from './use-nft-gallery-layout';

const breakpoint = {
  is2xl: ref<boolean>(false),
  isMd: ref<boolean>(false),
  isSm: ref<boolean>(false),
  isSmAndDown: ref<boolean>(false),
};

vi.mock('@rotki/ui-library', async () => {
  const actual = await vi.importActual<typeof import('@rotki/ui-library')>('@rotki/ui-library');
  return { ...actual, useBreakpoint: (): typeof breakpoint => breakpoint };
});

function nftList(count: number): ComputedRef<GalleryNft[]> {
  const items = Array.from({ length: count }, (_, i) => createMock<GalleryNft>({ tokenIdentifier: `nft-${i}` }));
  return computed<GalleryNft[]>(() => items);
}

describe('useNftGalleryLayout', () => {
  beforeEach(() => {
    set(breakpoint.is2xl, false);
    set(breakpoint.isMd, false);
    set(breakpoint.isSm, false);
    set(breakpoint.isSmAndDown, false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ['isSmAndDown', 1],
    ['isSm', 2],
    ['isMd', 6],
    ['is2xl', 10],
  ] as const)('should pick the first limit for %s', (key, expected) => {
    set(breakpoint[key], true);
    const { firstLimit, itemsPerPage } = useNftGalleryLayout(nftList(0));
    expect(get(firstLimit)).toBe(expected);
    // watchImmediate syncs itemsPerPage to the first limit
    expect(get(itemsPerPage)).toBe(expected);
  });

  it('should default the first limit to 8', () => {
    const { firstLimit } = useNftGalleryLayout(nftList(0));
    expect(get(firstLimit)).toBe(8);
  });

  it('should derive the page-size limits from the first limit', () => {
    set(breakpoint.isMd, true); // first = 6
    const { limits } = useNftGalleryLayout(nftList(0));
    expect(get(limits)).toEqual([6, 12, 24]);
  });

  it('should page the visible nfts by items-per-page', () => {
    const { visibleNfts, page, paginationData } = useNftGalleryLayout(nftList(20));
    // default first limit 8
    expect(get(visibleNfts)).toHaveLength(8);
    expect(get(visibleNfts)[0].tokenIdentifier).toBe('nft-0');

    set(paginationData, { ...get(paginationData), page: 2 });
    expect(get(page)).toBe(2);
    expect(get(visibleNfts)[0].tokenIdentifier).toBe('nft-8');
  });

  it('should expose and update pagination data', () => {
    const { paginationData } = useNftGalleryLayout(nftList(20));
    expect(get(paginationData)).toMatchObject({ limit: 8, page: 1, total: 20 });

    set(paginationData, { limit: 4, limits: [4, 8, 16], page: 3, total: 20 });
    expect(get(paginationData)).toMatchObject({ limit: 4, page: 3 });
  });
});
