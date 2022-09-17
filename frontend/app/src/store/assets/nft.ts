import { SupportedAsset } from '@rotki/common/lib/data';
import { get, MaybeRef } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { ComputedRef } from 'vue';
import { useBalancesStore } from '@/store/balances';
import { NonFungibleBalance } from '@/types/nfbalances';
import { isNft } from '@/utils/nft';

export type NftAsset = SupportedAsset & {
  imageUrl?: string;
  collectionName?: string;
};

export const useNftAssetInfoStore = defineStore('assets/nfts', () => {
  const { nfBalances } = storeToRefs(useBalancesStore());

  const getNftDetails = (
    identifier: MaybeRef<string>
  ): ComputedRef<NftAsset | null> =>
    computed(() => {
      const id = get(identifier);

      if (!isNft(id)) {
        return null;
      }

      const balances = get(nfBalances) as NonFungibleBalance[];
      const balance = balances.find(item => item.id === id);

      if (!balance) {
        return null;
      }

      return {
        identifier: balance.id,
        symbol: balance.name,
        name: balance.name,
        assetType: 'ethereum_token',
        imageUrl: balance.imageUrl,
        collectionName: balance.collectionName
      } as NftAsset;
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
