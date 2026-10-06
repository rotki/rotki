import { redirectAfterUnlock } from '@/modules/shell/layout/login-redirect';

interface UseAppNavigationReturn {
  navigateAfterUnlock: () => Promise<void>;
  navigateToUserCreation: () => Promise<void>;
  navigateToUserLogin: () => Promise<void>;
}

export function useAppNavigation(): UseAppNavigationReturn {
  const router = useRouter();
  const navigateToUserLogin = async (): Promise<void> => {
    if (get(router.currentRoute).name === '/user/login/')
      return;

    await router.push({ name: '/user/login/' });
  };

  const navigateToUserCreation = async (): Promise<void> => {
    await router.push({ name: '/user/create/' });
  };

  /** Opens the page the login was redirected from, or the dashboard when there is none. */
  const navigateAfterUnlock = async (): Promise<void> => {
    const target = redirectAfterUnlock(get(router.currentRoute).query);
    await router.push(target ?? { name: '/dashboard/' });
  };

  return {
    navigateAfterUnlock,
    navigateToUserCreation,
    navigateToUserLogin,
  };
}
