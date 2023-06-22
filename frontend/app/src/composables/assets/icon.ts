export const useAssetIcon = createSharedComposable(() => {
  const lastRefreshedAssetIcon: Ref<number> = ref(0);

  const setLastRefreshedAssetIcon = () => {
    set(lastRefreshedAssetIcon, Date.now());
  };

  onBeforeMount(() => {
    setLastRefreshedAssetIcon();
  });

  const { assetImageUrl } = useAssetIconApi();

  const getAssetImageUrl = (identifier: string, timestamp?: number) =>
    assetImageUrl(identifier, timestamp ?? get(lastRefreshedAssetIcon));

  return {
    getAssetImageUrl,
    setLastRefreshedAssetIcon
  };
});
