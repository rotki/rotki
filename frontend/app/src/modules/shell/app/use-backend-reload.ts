import { Severity } from '@rotki/common';
import { useLogout } from '@/modules/auth/use-logout';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useBackendConnection } from '@/modules/shell/app/use-backend-connection';
import {
  type BackendRestartResult,
  BackendRestartStatus,
  useBackendManagement,
} from '@/modules/shell/app/use-backend-management';

interface UseBackendReloadReturn {
  reload: () => Promise<BackendRestartResult>;
}

/**
 * Bounce the backend so it picks up a change it cannot see any other way, and settle the
 * session around it.
 *
 * The asset-database flows (an update, a reset) write to the global database, which the
 * running backend has already read into memory. Only a restart makes it reload, and that
 * restart is itself a logout: core's graceful shutdown runs the same
 * `Rotkehlchen.logout()` that settles the user database, so what follows is frontend
 * cleanup rather than a second logout.
 *
 * Both callers did this identically and inline, which is how they came to share a bug:
 * a restart that never happened was indistinguishable from one that did, so they logged
 * out and reported completion either way, leaving the user to sign back in to a backend
 * still holding the data they had just replaced.
 */
export function useBackendReload(): UseBackendReloadReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationDispatcher();
  const { restartBackend } = useBackendManagement();
  const { connect } = useBackendConnection();
  const { logout } = useLogout();
  const { setConnected } = useMainStore();
  const { logged } = storeToRefs(useSessionAuthStore());

  const reload = async (): Promise<BackendRestartResult> => {
    setConnected(false);
    const result = await restartBackend();

    if (result.status === BackendRestartStatus.failed) {
      notify({
        display: true,
        message: t('backend_reload.failed.message', { message: result.message ?? '' }),
        severity: Severity.ERROR,
        title: t('backend_reload.failed.title'),
      });
      connect();
      return result;
    }

    if (get(logged))
      await logout(true, { skipBackendCall: result.status === BackendRestartStatus.restarted });

    connect();
    return result;
  };

  return { reload };
}
