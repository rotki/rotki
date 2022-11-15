import { Routes } from '@/router/routes';

export const useAppNavigation = () => {
  const router = useRouter();
  const navigateToUserLogin = async () => {
    await router.push(Routes.USER_LOGIN);
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
