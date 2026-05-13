import { Routes } from '@/router/routes';

interface UseAppNavigationReturn {
  navigateToDashboard: () => Promise<void>;
  navigateToUserCreation: () => Promise<void>;
  navigateToUserLogin: () => Promise<void>;
}

export function useAppNavigation(): UseAppNavigationReturn {
  const router = useRouter();
  const navigateToUserLogin = async (): Promise<void> => {
    if (get(router.currentRoute).path === Routes.USER_LOGIN)
      return;

    await router.push(Routes.USER_LOGIN);
  };

  const navigateToUserCreation = async (): Promise<void> => {
    await router.push(Routes.USER_CREATE);
  };

  const navigateToDashboard = async (): Promise<void> => {
    await router.push(Routes.DASHBOARD);
  };

  return {
    navigateToDashboard,
    navigateToUserCreation,
    navigateToUserLogin,
  };
}
