import { isEqual } from 'lodash-es';
import { Routes } from '@/router/routes';

export function useAppNavigation() {
  const router = useRouter();
  const navigateToUserLogin = async (disableNoUserRedirection: boolean = false) => {
    const newQuery = disableNoUserRedirection ? { disableNoUserRedirection: '1' } : {};
    const { path, query } = get(router.currentRoute);
    if (path === Routes.USER_LOGIN && isEqual(query, newQuery))
      return;

    await router.push({
      path: '/user/login',
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
