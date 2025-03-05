import { promiseTimeout } from '@vueuse/core';
import { useAppNavigation } from '@/composables/navigation';
import { logger } from '@/utils/logging';
import { useSessionAuthStore } from '@/store/session/auth';
import { useInterop } from '@/composables/electron-interop';
import { useMessageStore } from '@/store/message';
import { useUsersApi } from '@/composables/api/session/users';
import type { ActionStatus } from '@/types/action';

interface UseLogoutReturn {
  logout: (navigate?: boolean) => Promise<void>;
  logoutRemoteSession: () => Promise<ActionStatus>;
}

export function useLogout(): UseLogoutReturn {
  const { navigateToUserLogin } = useAppNavigation();
  const { logged, username } = storeToRefs(useSessionAuthStore());
  const { setMessage } = useMessageStore();
  const { resetTray } = useInterop();
  const { loggedUsers: getLoggedUsers, logout: callLogout } = useUsersApi();

  const logout = async (navigate: boolean = true): Promise<void> => {
    set(logged, false);
    const user = get(username); // save the username, after the await below, it is reset
    // allow some time for the components to leave the dom completely and show loading overlay
    await promiseTimeout(1500);
    resetTray();
    try {
      await callLogout(user);
    }
    catch (error: any) {
      logger.error(error);
      setMessage({
        description: error.message,
        title: 'Logout failed',
      });
    }

    if (navigate)
      await navigateToUserLogin();
  };

  const logoutRemoteSession = async (): Promise<ActionStatus> => {
    try {
      const loggedUsers = await getLoggedUsers();
      for (const user of loggedUsers)
        await callLogout(user);

      return { success: true };
    }
    catch (error: any) {
      setMessage({
        description: error.message,
        title: 'Remote session logout failure',
      });
      return { message: error.message, success: false };
    }
  };

  return {
    logout,
    logoutRemoteSession,
  };
}
