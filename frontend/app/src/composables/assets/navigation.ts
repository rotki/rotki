import type { Ref } from 'vue';

interface UseAssetPageNavigationReturn { navigateToDetails: () => Promise<void> }

export function useAssetPageNavigation(asset: Ref<string>, collectionParent?: Ref<boolean>): UseAssetPageNavigationReturn {
  const router = useRouter();
  const navigateToDetails = async (): Promise<void> => {
    await router.push({
      name: '/assets/[identifier]',
      params: {
        identifier: get(asset),
      },
      ...(!get(collectionParent)
        ? {}
        : {
            query: {
              collectionParent: 'true',
            },
          }),
    });
  };

  return {
    navigateToDetails,
  };
}
