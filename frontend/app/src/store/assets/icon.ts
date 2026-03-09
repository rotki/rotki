import { useAssetIconApi } from '@/composables/api/assets/icon';
import { useAssetIconCheck } from '@/modules/assets/use-asset-icon-check';
import { isBlockchain } from '@/types/blockchain/chains';

export const useAssetIconStore = defineStore('assets/icon', () => {
  const lastRefreshedAssetIcon = ref<number>(0);

  const setLastRefreshedAssetIcon = (): void => {
    set(lastRefreshedAssetIcon, Date.now());
  };

  const { assetImageUrl } = useAssetIconApi();

  const getAssetImageUrl = (identifier: string): string => {
    const id = isBlockchain(identifier) ? identifier.toUpperCase() : identifier;
    return assetImageUrl(id, get(lastRefreshedAssetIcon));
  };

  const { checkIfAssetExists } = useAssetIconCheck(lastRefreshedAssetIcon);

  return {
    checkIfAssetExists,
    getAssetImageUrl,
    setLastRefreshedAssetIcon,
  };
});
