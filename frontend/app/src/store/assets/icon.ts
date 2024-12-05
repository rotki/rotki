import { isBlockchain } from '@/types/blockchain/chains';
import { useAssetIconApi } from '@/composables/api/assets/icon';

export const useAssetIconStore = defineStore('assets/icon', () => {
  const lastRefreshedAssetIcon = ref<number>(0);

  const setLastRefreshedAssetIcon = (): void => {
    set(lastRefreshedAssetIcon, Date.now());
  };

  onBeforeMount(() => {
    setLastRefreshedAssetIcon();
  });

  const { assetImageUrl } = useAssetIconApi();

  const getAssetImageUrl = (identifier: string): string => {
    const id = isBlockchain(identifier) ? identifier.toUpperCase() : identifier;
    return assetImageUrl(id, get(lastRefreshedAssetIcon));
  };

  return {
    getAssetImageUrl,
    setLastRefreshedAssetIcon,
  };
});
