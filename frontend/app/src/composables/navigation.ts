import { isEqual } from 'lodash-es';
import { Routes } from '@/router/routes';
import { router } from '@/router';

export function useAppNavigation() {
  const navigateToUserLogin = async (
    disableNoUserRedirection: boolean = false,
  ) => {
    const newQuery = disableNoUserRedirection ? { disableNoUserRedirection: '1' } : {};
    const { path, query } = router.currentRoute;
    if (path === Routes.USER_LOGIN && isEqual(query, newQuery))
      return;

    await router.push({
      path: Routes.USER_LOGIN,
      query: newQuery,
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
    navigateToUserLogin,
  };
}
