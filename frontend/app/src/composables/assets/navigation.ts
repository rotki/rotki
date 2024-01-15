import { Routes } from '@/router/routes';

export function useAssetPageNavigation(asset: Ref<string>) {
  const router = useRouter();
  const navigateToDetails = async () => {
    await router.push({
      path: Routes.ASSETS.replace(':identifier', encodeURIComponent(get(asset))),
    });
  };

  return {
    navigateToDetails,
  };
}
