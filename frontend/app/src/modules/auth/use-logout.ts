import type { ActionStatus } from '@/modules/core/common/action';
import { promiseTimeout } from '@vueuse/core';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { api } from '@/modules/core/api/rotki-api';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { endSession, finishPendingWrites } from '@/modules/core/session/session-lifecycle';
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

/** A logout reports its failures after its session ended, to the logged-out screen. */
const SESSIONLESS = { sessionless: true } as const;

/**
 * Drops every request still queued or in flight, sessionless ones included.
 *
 * @remarks
 * The first thing a remote-session logout does. This tab holds no session then, so ending one
 * would cancel nothing.
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

  /**
   * Ends the session, then tears the logged-in state down and logs the user out of the backend.
   *
   * @remarks
   * Only the writes still persisting the user's input are waited for first; the session ends before
   * anything else awaits. The backend keeps serving this user until the logout call lands, so
   * anything still running for the session must already be refused by then.
   */
  const logout = async (navigate: boolean = true, options: LogoutOptions = {}): Promise<void> => {
    await finishPendingWrites();
    endSession();
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
        showErrorMessage('Logout failed', getErrorMessage(error), SESSIONLESS);
      }
    }

    try {
      await resetMcpSession();
    }
    catch (error: unknown) {
      logger.error(error);
      showErrorMessage('MCP logout failed', getErrorMessage(error), SESSIONLESS);
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
      showErrorMessage('Remote session logout failure', message, SESSIONLESS);
      return { message, success: false };
    }
  };

  return {
    logout,
    logoutRemoteSession,
  };
}
