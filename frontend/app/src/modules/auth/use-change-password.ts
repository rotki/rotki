import type { ActionStatus } from '@/modules/core/common/action';
import type { ChangePasswordPayload } from '@/modules/session/types';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useUsersApi } from '@/modules/auth/use-users-api';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseChangePasswordReturn {
  /** Changes the password; reports nothing itself, the form naming the outcome. */
  changePassword: (payload: ChangePasswordPayload) => Promise<ActionStatus>;
}

export function useChangePassword(): UseChangePasswordReturn {
  const { username } = storeToRefs(useSessionAuthStore());
  const { changeUserPassword, colibriLogin, colibriLogout } = useUsersApi();
  const { clearPassword, isPackaged } = useInterop();
  const { t } = useI18n({ useScope: 'global' });

  const changePassword = async ({ currentPassword, newPassword }: ChangePasswordPayload): Promise<ActionStatus> => {
    try {
      const success = await changeUserPassword(get(username), currentPassword, newPassword);
      if (!success)
        return { message: t('common.change_not_applied'), success };

      try {
        await colibriLogout();
        await colibriLogin({ username: get(username), password: newPassword });
      }
      catch (error: unknown) {
        logger.error('Failed to re-authenticate with colibri after password change', error);
      }

      if (isPackaged) {
        clearPassword()
          .then(() => logger.info('clear complete'))
          .catch(error => logger.error(error));
      }

      return { success };
    }
    catch (error: unknown) {
      return { message: getErrorMessage(error), success: false };
    }
  };

  return {
    changePassword,
  };
}
