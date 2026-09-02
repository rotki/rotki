import type { ActionStatus } from '@/modules/core/common/action';
import { promiseTimeout } from '@vueuse/core';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { api } from '@/modules/core/api';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSchedulerState } from '@/modules/session/use-scheduler-state';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';
import { disconnectWalletIfActive } from '@/modules/wallet/use-wallet-store';

interface LogoutOptions {
  navigate?: boolean;
  /**
   * Skip the backend logout call, for callers that have just restarted the
   * backend.
   *
   * A restart is already a logout: starling terminates core gracefully, and
   * core's SIGTERM path runs the very same `Rotkehlchen.logout()` the HTTP
   * endpoint would, so the user DB is settled either way. Calling it afterwards
   * would only reach a backend with nobody logged in, which answers 409 and
   * surfaces a spurious "Logout failed" to the user.
   */
  skipBackendCall?: boolean;
}

interface UseLogoutReturn {
  logout: (navigate?: boolean, options?: LogoutOptions) => Promise<void>;
  logoutRemoteSession: () => Promise<ActionStatus>;
}

/** Long enough for the components to leave the DOM and the loading overlay to take over. */
const DOM_TEARDOWN_MS = 1500;

/**
 * Drops every request still queued or in flight.
 *
 * @remarks
 * The first thing a logout does. A response that lands after the session is torn down writes into
 * stores the next user is about to inherit.
 */
function cancelInFlightRequests(): void {
  api.cancelAllQueued();
  api.cancel();
}

export function useLogout(): UseLogoutReturn {
  const { navigateToUserLogin } = useAppNavigation();
  const { logged, username } = storeToRefs(useSessionAuthStore());
  const { showErrorMessage } = useNotifications();
  const { notifyUserLogout, resetMcpSession, resetTray } = useInterop();
  const { loggedUsers: getLoggedUsers, logout: callLogout } = useUsersApi();
  const { reset: resetSchedulerState } = useSchedulerState();

  /**
   * Tears the wallet bridge down, main process first.
   *
   * @remarks
   * Electron has to be told before the renderer disconnects, or it is left holding bridge
   * connections for a session that no longer exists.
   */
  const closeWalletBridge = async (): Promise<void> => {
    notifyUserLogout();
    await disconnectWalletIfActive();
  };

  const logout = async (navigate: boolean = true, options: LogoutOptions = {}): Promise<void> => {
    cancelInFlightRequests();
    resetSchedulerState();
    await closeWalletBridge();

    set(logged, false);
    const user = get(username); // save the username, after the await below, it is reset
    await promiseTimeout(DOM_TEARDOWN_MS);
    resetTray();

    if (!options.skipBackendCall) {
      try {
        await callLogout(user);
      }
      catch (error: unknown) {
        logger.error(error);
        showErrorMessage('Logout failed', getErrorMessage(error));
      }
    }

    try {
      await resetMcpSession();
    }
    catch (error: unknown) {
      logger.error(error);
      showErrorMessage('MCP logout failed', getErrorMessage(error));
    }

    if (navigate)
      await navigateToUserLogin();
  };

  const logoutRemoteSession = async (): Promise<ActionStatus> => {
    cancelInFlightRequests();

    try {
      await disconnectWalletIfActive();
      const loggedUsers = await getLoggedUsers();
      for (const user of loggedUsers)
        await callLogout(user);
      await resetMcpSession();

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
