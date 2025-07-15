import { isEqual } from 'es-toolkit';
import { Routes } from '@/router/routes';

interface UseAppNavigationReturn {
  navigateToDashboard: () => Promise<void>;
  navigateToUserCreation: () => Promise<void>;
  navigateToUserLogin: (disableNoUserRedirection?: boolean) => Promise<void>;
}

export function useAppNavigation(): UseAppNavigationReturn {
  const router = useRouter();
  const navigateToUserLogin = async (disableNoUserRedirection: boolean = false): Promise<void> => {
    const newQuery = disableNoUserRedirection ? { disableNoUserRedirection: '1' } : {};
    const { path, query } = get(router.currentRoute);
    if (path === Routes.USER_LOGIN && isEqual(query, newQuery))
      return;

    await router.push({
      path: '/user/login',
      query: newQuery,
    });
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
