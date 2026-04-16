import type { ActionStatus } from '@/modules/common/action';
import { promiseTimeout } from '@vueuse/core';
import { useUsersApi } from '@/composables/api/session/users';
import { useInterop } from '@/composables/electron-interop';
import { useAppNavigation } from '@/composables/navigation';
import { useSchedulerState } from '@/composables/session/use-scheduler-state';
import { api } from '@/modules/api';
import { logger } from '@/modules/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useSessionAuthStore } from '@/store/session/auth';

interface UseLogoutReturn {
  logout: (navigate?: boolean) => Promise<void>;
  logoutRemoteSession: () => Promise<ActionStatus>;
}

export function useLogout(): UseLogoutReturn {
  const { navigateToUserLogin } = useAppNavigation();
  const { logged, username } = storeToRefs(useSessionAuthStore());
  const { showErrorMessage } = useNotifications();
  const { notifyUserLogout, resetTray } = useInterop();
  const { loggedUsers: getLoggedUsers, logout: callLogout } = useUsersApi();
  const { disconnect: disconnectWallet } = useWalletStore();
  const { reset: resetSchedulerState } = useSchedulerState();

  const logout = async (navigate: boolean = true): Promise<void> => {
    // Cancel all pending API requests first to prevent race conditions
    api.cancelAllQueued();
    api.cancel();

    // Reset scheduler state (backend resets scheduler separately)
    resetSchedulerState();

    // Notify electron to cleanup wallet bridge connections BEFORE disconnecting
    notifyUserLogout();

    await disconnectWallet();
    set(logged, false);
    const user = get(username); // save the username, after the await below, it is reset
    // allow some time for the components to leave the dom completely and show loading overlay
    await promiseTimeout(1500);
    resetTray();

    try {
      await callLogout(user);
    }
    catch (error: unknown) {
      logger.error(error);
      showErrorMessage('Logout failed', getErrorMessage(error));
    }

    if (navigate)
      await navigateToUserLogin();
  };

  const logoutRemoteSession = async (): Promise<ActionStatus> => {
    // Cancel all pending API requests first to prevent race conditions
    api.cancelAllQueued();
    api.cancel();

    try {
      await disconnectWallet();
      const loggedUsers = await getLoggedUsers();
      for (const user of loggedUsers)
        await callLogout(user);

      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      showErrorMessage('Remote session logout failure', message);
      return { message, success: false };
    }
  };

  return {
    logout,
    logoutRemoteSession,
  };
}
