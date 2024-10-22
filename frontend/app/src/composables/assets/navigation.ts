import type { Ref } from 'vue';

interface UseAssetPageNavigationReturn { navigateToDetails: () => Promise<void> }

export function useAssetPageNavigation(asset: Ref<string>): UseAssetPageNavigationReturn {
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
