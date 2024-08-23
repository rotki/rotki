export function useAssetPageNavigation(asset: Ref<string>) {
  const router = useRouter();
  const navigateToDetails = async (): Promise<void> => {
    await router.push({
      name: '/assets/[identifier]',
      params: {
        identifier: get(asset),
      },
    });
  };

  return {
    navigateToDetails,
  };
}
