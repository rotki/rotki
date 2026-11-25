import { type MaybeRefOrGetter, toValue } from 'vue';
import { useRouter } from 'vue-router';

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
