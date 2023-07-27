import { isBlockchain } from '@/types/blockchain/chains';

export const useAssetIcon = createSharedComposable(() => {
  const lastRefreshedAssetIcon: Ref<number> = ref(0);

  const setLastRefreshedAssetIcon = () => {
    set(lastRefreshedAssetIcon, Date.now());
  };

  onBeforeMount(() => {
    setLastRefreshedAssetIcon();
  });

  const { assetImageUrl } = useAssetIconApi();

  const getAssetImageUrl = (identifier: string, timestamp?: number): string => {
    const id = isBlockchain(identifier) ? identifier.toUpperCase() : identifier;
    return assetImageUrl(id, timestamp ?? get(lastRefreshedAssetIcon));
  };

  return {
    getAssetImageUrl,
    setLastRefreshedAssetIcon
  };
});
