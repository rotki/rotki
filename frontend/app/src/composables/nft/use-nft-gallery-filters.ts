import type { ComputedRef, Ref } from 'vue';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { GalleryNft, Nfts } from '@/types/nfts';
import { assert, BigNumber } from '@rotki/common';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { uniqueStrings } from '@/utils/data';

interface UseNftGalleryFiltersReturn {
  availableAddresses: ComputedRef<string[]>;
  collections: ComputedRef<string[]>;
  items: ComputedRef<GalleryNft[]>;
  selectedAccounts: Ref<BlockchainAccount<AddressData>[]>;
  selectedCollection: Ref<string | undefined>;
  sortBy: Ref<'name' | 'price' | 'collection'>;
  sortDescending: Ref<boolean>;
  updateSortBy: (value: string) => void;
}

export function useNftGalleryFilters(
  nfts: ComputedRef<GalleryNft[]>,
  perAccount: Ref<Nfts | null>,
): UseNftGalleryFiltersReturn {
  // State
  const selectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);
  const selectedCollection = ref<string | undefined>();
  const sortBy = ref<'name' | 'price' | 'collection'>('name');
  const sortDescending = ref<boolean>(false);

  // Computed properties
  const availableAddresses = computed<string[]>(() => get(perAccount) ? Object.keys(get(perAccount)!) : []);

  const collections = computed<string[]>(() => {
    if (!get(nfts))
      return [];

    return get(nfts)
      .map(({ collection }) => collection.name ?? '')
      .filter(uniqueStrings);
  });

  const items = computed<GalleryNft[]>(() => {
    const accounts = get(selectedAccounts);
    const selection = get(selectedCollection);
    const hasAccounts = accounts.length > 0;
    const allNfts = [...get(nfts)];

    if (hasAccounts || selection) {
      return allNfts
        .filter(({ address, collection }) => {
          const sameAccount = hasAccounts ? accounts.find(account => getAccountAddress(account) === address) : true;
          const sameCollection = selection ? selection === collection.name : true;
          return sameAccount && sameCollection;
        })
        .sort((a, b) => sortNfts(sortBy, sortDescending, a, b));
    }

    return allNfts.sort((a, b) => sortNfts(sortBy, sortDescending, a, b));
  });

  // Methods
  function updateSortBy(value: string): void {
    assert(['name', 'price', 'collection'].includes(value));
    set(sortBy, value as 'name' | 'price' | 'collection');
  }

  function sortNfts(
    sortBy: Ref<'name' | 'price' | 'collection'>,
    sortDesc: Ref<boolean>,
    a: GalleryNft,
    b: GalleryNft,
  ): number {
    const sortProp = get(sortBy);
    const desc = get(sortDesc);
    const isCollection = sortProp === 'collection';
    const aElement = isCollection ? a.collection.name : a[sortProp];
    const bElement = isCollection ? b.collection.name : b[sortProp];

    if (typeof aElement === 'string' && typeof bElement === 'string') {
      return desc
        ? bElement.localeCompare(aElement, 'en', { sensitivity: 'base' })
        : aElement.localeCompare(bElement, 'en', { sensitivity: 'base' });
    }
    else if (aElement instanceof BigNumber && bElement instanceof BigNumber) {
      return (desc ? bElement.minus(aElement) : aElement.minus(bElement)).toNumber();
    }
    else if (aElement === null && bElement === null) {
      return 0;
    }
    else if (aElement && !bElement) {
      return desc ? 1 : -1;
    }
    else if (!aElement && bElement) {
      return desc ? -1 : 1;
    }
    return 0;
  }

  return {
    availableAddresses,
    collections,
    items,
    selectedAccounts,
    selectedCollection,
    sortBy,
    sortDescending,
    updateSortBy,
  };
}
