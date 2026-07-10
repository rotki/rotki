interface UseAppNavigationReturn {
  navigateToDashboard: () => Promise<void>;
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

  const navigateToDashboard = async (): Promise<void> => {
    await router.push({ name: '/dashboard/' });
  };

  return {
    navigateToDashboard,
    navigateToUserCreation,
    navigateToUserLogin,
  };
}
