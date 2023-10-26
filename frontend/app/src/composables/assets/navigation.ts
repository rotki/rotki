import { Routes } from '@/router/routes';

export const useAssetPageNavigation = (asset: Ref<string>) => {
  const router = useRouter();
  const navigateToDetails = async () => {
    await router.push({
      path: Routes.ASSETS.replace(':identifier', encodeURIComponent(get(asset)))
    });
  };

  return {
    navigateToDetails
  };
};
