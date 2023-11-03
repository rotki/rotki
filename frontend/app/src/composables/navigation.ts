import { Routes } from '@/router/routes';

export const useAppNavigation = () => {
  const router = useRouter();
  const navigateToUserLogin = async (
    disableNoUserRedirection: boolean = false
  ) => {
    await router.push({
      path: Routes.USER_LOGIN,
      ...(disableNoUserRedirection
        ? { query: { disableNoUserRedirection: '1' } }
        : {})
    });
  };

  const navigateToUserCreation = async () => {
    await router.push(Routes.USER_CREATE);
  };

  const navigateToDashboard = async () => {
    await router.push(Routes.DASHBOARD);
  };

  return {
    navigateToDashboard,
    navigateToUserCreation,
    navigateToUserLogin
  };
};
