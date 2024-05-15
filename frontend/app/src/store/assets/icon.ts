import { isBlockchain } from '@/types/blockchain/chains';

export const useAssetIconStore = defineStore('assets/icon', () => {
  const lastRefreshedAssetIcon: Ref<number> = ref(0);

  const setLastRefreshedAssetIcon = () => {
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
