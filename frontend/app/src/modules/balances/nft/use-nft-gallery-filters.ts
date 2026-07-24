import type { ComputedRef, Ref } from 'vue';
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { GalleryNft, Nfts } from '@/modules/assets/nfts';
import { assert, BigNumber } from '@rotki/common';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { uniqueStrings } from '@/modules/core/common/data/data';

type NftSortKey = 'name' | 'price' | 'collection';

type NftSortValue = string | BigNumber | null;

function getSortValue(nft: GalleryNft, sortProp: NftSortKey): NftSortValue {
  return sortProp === 'collection' ? nft.collection.name : nft[sortProp];
}

function compareNullableNft(a: NftSortValue, b: NftSortValue, desc: boolean): number {
  if (a && !b)
    return desc ? 1 : -1;
  if (!a && b)
    return desc ? -1 : 1;
  return 0;
}

function compareNftValues(a: NftSortValue, b: NftSortValue, desc: boolean): number {
  if (typeof a === 'string' && typeof b === 'string') {
    return desc
      ? b.localeCompare(a, 'en', { sensitivity: 'base' })
      : a.localeCompare(b, 'en', { sensitivity: 'base' });
  }
  if (a instanceof BigNumber && b instanceof BigNumber)
    return (desc ? b.minus(a) : a.minus(b)).toNumber();
  return compareNullableNft(a, b, desc);
}

interface UseNftGalleryFiltersReturn {
  availableAddresses: ComputedRef<string[]>;
  collections: ComputedRef<string[]>;
  items: ComputedRef<GalleryNft[]>;
  modelSelectedAccounts: Ref<BlockchainAccount<AddressData>[]>;
  modelSelectedCollection: Ref<string | undefined>;
  modelSortBy: Ref<'name' | 'price' | 'collection'>;
  modelSortDescending: Ref<boolean>;
  updateSortBy: (value: string) => void;
}

export function useNftGalleryFilters(
  nfts: ComputedRef<GalleryNft[]>,
  perAccount: Ref<Nfts | null>,
): UseNftGalleryFiltersReturn {
  // State
  const modelSelectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);
  const modelSelectedCollection = ref<string | undefined>();
  const modelSortBy = shallowRef<'name' | 'price' | 'collection'>('name');
  const modelSortDescending = shallowRef<boolean>(false);

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
    const accounts = get(modelSelectedAccounts);
    const selection = get(modelSelectedCollection);
    const hasAccounts = accounts.length > 0;
    const allNfts = [...get(nfts)];

    if (hasAccounts || selection) {
      return allNfts
        .filter(({ address, collection }) => {
          const sameAccount = hasAccounts ? accounts.find(account => getAccountAddress(account) === address) : true;
          const sameCollection = selection ? selection === collection.name : true;
          return sameAccount && sameCollection;
        })
        .sort((a, b) => sortNfts(modelSortBy, modelSortDescending, a, b));
    }

    return allNfts.sort((a, b) => sortNfts(modelSortBy, modelSortDescending, a, b));
  });

  // Methods
  function updateSortBy(value: string): void {
    assert(['name', 'price', 'collection'].includes(value));
    set(modelSortBy, value as 'name' | 'price' | 'collection');
  }

  function sortNfts(
    sortProperty: Ref<NftSortKey>,
    sortDesc: Ref<boolean>,
    a: GalleryNft,
    b: GalleryNft,
  ): number {
    const sortProp = get(sortProperty);
    const desc = get(sortDesc);
    return compareNftValues(getSortValue(a, sortProp), getSortValue(b, sortProp), desc);
  }

  return {
    availableAddresses,
    collections,
    items,
    modelSelectedAccounts,
    modelSelectedCollection,
    modelSortBy,
    modelSortDescending,
    updateSortBy,
  };
}
