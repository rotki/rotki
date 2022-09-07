import { get, MaybeRef } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useBalancesStore } from '@/store/balances';
import { NonFungibleBalance } from '@/store/balances/types';

export const isVideo = (url: string | null): boolean => {
  const videoExtensions = ['mp4', 'mov', 'webm', 'ogg'];
  return videoExtensions.some(
    extension => url !== null && url.endsWith(extension)
  );
};

export const isNft = (address?: string) => {
  if (!address) return false;
  return address.startsWith('_nft_');
};

export const getNftBalance = (
  identifier: MaybeRef<string>
): NonFungibleBalance | null => {
  const { nfBalances } = storeToRefs(useBalancesStore());
  const id = get(identifier);

  const balances = get(nfBalances) as NonFungibleBalance[];
  return balances.find(item => item.id === id) || null;
};
