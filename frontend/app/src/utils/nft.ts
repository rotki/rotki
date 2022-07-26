import { get } from '@vueuse/core';
import { setupGeneralBalances } from '@/composables/balances';
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
  identifier: string
): NonFungibleBalance | null => {
  const { nfBalances } = setupGeneralBalances();

  return get(nfBalances).find(item => item.id === identifier) || null;
};
