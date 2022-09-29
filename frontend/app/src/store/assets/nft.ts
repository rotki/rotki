import { MaybeRef } from '@vueuse/core';
import { ComputedRef } from 'vue';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import { AssetInfoWithId } from '@/types/assets';
import { isNft } from '@/utils/nft';

export type NftAsset = AssetInfoWithId & {
  imageUrl?: string;
  collectionName?: string;
};

export const useNftAssetInfoStore = defineStore('assets/nfts', () => {
  const { nonFungibleBalances } = storeToRefs(useNonFungibleBalancesStore());

  const getNftDetails = (
    identifier: MaybeRef<string>
  ): ComputedRef<NftAsset | null> =>
    computed(() => {
      const id = get(identifier);

      if (!isNft(id)) {
        return null;
      }

      const balances = get(nonFungibleBalances);
      const balance = balances.find(item => item.id === id);

      if (!balance) {
        return null;
      }

      return {
        identifier: balance.id,
        symbol: balance.name ?? '',
        name: balance.name ?? '',
        imageUrl: balance.imageUrl ?? undefined,
        collectionName: balance.collectionName ?? undefined
      };
    });

  return {
    getNftDetails
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useNftAssetInfoStore, import.meta.hot)
  );
}
