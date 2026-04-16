import type { MaybeRefOrGetter } from 'vue';

interface UseAssetPageNavigationReturn { navigateToDetails: () => Promise<void> }

export function useAssetPageNavigation(asset: MaybeRefOrGetter<string>, collectionParent?: MaybeRefOrGetter<boolean>): UseAssetPageNavigationReturn {
  const router = useRouter();
  const navigateToDetails = async (): Promise<void> => {
    await router.push({
      name: '/assets/[identifier]',
      params: {
        identifier: toValue(asset),
      },
      ...(!toValue(collectionParent)
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
