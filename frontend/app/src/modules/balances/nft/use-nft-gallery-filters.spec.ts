import type { ComputedRef } from 'vue';
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { GalleryNft, Nfts } from '@/modules/assets/nfts';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNftGalleryFilters } from './use-nft-gallery-filters';

vi.mock('@/modules/accounts/account-utils', () => ({
  getAccountAddress: (account: { data: { address: string } }): string => account.data.address,
}));

function nft(overrides: { address?: string; name?: string; price?: number; collection?: string }): GalleryNft {
  return createMock<GalleryNft>({
    address: overrides.address ?? '0xabc',
    collection: createMock({ name: overrides.collection ?? 'Punks' }),
    name: overrides.name ?? 'NFT',
    price: bigNumberify(overrides.price ?? 1),
  });
}

function account(address: string): BlockchainAccount<AddressData> {
  return createMock<BlockchainAccount<AddressData>>({ data: { address } });
}

describe('useNftGalleryFilters', () => {
  let nfts: ComputedRef<GalleryNft[]>;
  let list: GalleryNft[];

  beforeEach(() => {
    list = [];
    nfts = computed<GalleryNft[]>(() => list);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should list available addresses from the per-account map', () => {
    const perAccount = ref<Nfts | null>({ '0x1': [], '0x2': [] });
    const { availableAddresses } = useNftGalleryFilters(nfts, perAccount);
    expect(get(availableAddresses)).toEqual(['0x1', '0x2']);
  });

  it('should return no addresses when the per-account map is null', () => {
    const { availableAddresses } = useNftGalleryFilters(nfts, ref(null));
    expect(get(availableAddresses)).toEqual([]);
  });

  it('should collect the unique collection names', () => {
    list = [nft({ collection: 'Punks' }), nft({ collection: 'Apes' }), nft({ collection: 'Punks' })];
    const { collections } = useNftGalleryFilters(nfts, ref(null));
    expect(get(collections)).toEqual(['Punks', 'Apes']);
  });

  it('should sort by name ascending by default', () => {
    list = [nft({ name: 'Zed' }), nft({ name: 'Alpha' })];
    const { items } = useNftGalleryFilters(nfts, ref(null));
    expect(get(items).map(n => n.name)).toEqual(['Alpha', 'Zed']);
  });

  it('should sort by price descending', () => {
    list = [nft({ name: 'a', price: 1 }), nft({ name: 'b', price: 9 })];
    const { items, sortBy, sortDescending } = useNftGalleryFilters(nfts, ref(null));
    set(sortBy, 'price');
    set(sortDescending, true);
    expect(get(items).map(n => n.name)).toEqual(['b', 'a']);
  });

  it('should filter by the selected collection', () => {
    list = [nft({ name: 'a', collection: 'Punks' }), nft({ name: 'b', collection: 'Apes' })];
    const { items, selectedCollection } = useNftGalleryFilters(nfts, ref(null));
    set(selectedCollection, 'Apes');
    expect(get(items).map(n => n.name)).toEqual(['b']);
  });

  it('should filter by the selected accounts', () => {
    list = [nft({ address: '0x1', name: 'a' }), nft({ address: '0x2', name: 'b' })];
    const { items, selectedAccounts } = useNftGalleryFilters(nfts, ref(null));
    set(selectedAccounts, [account('0x2')]);
    expect(get(items).map(n => n.name)).toEqual(['b']);
  });

  it('should validate the sort key on update', () => {
    const { sortBy, updateSortBy } = useNftGalleryFilters(nfts, ref(null));
    updateSortBy('collection');
    expect(get(sortBy)).toBe('collection');
    expect(() => updateSortBy('bogus')).toThrow();
  });
});
