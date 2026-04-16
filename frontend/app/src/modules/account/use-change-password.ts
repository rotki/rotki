import type { ActionStatus } from '@/modules/common/action';
import type { ChangePasswordPayload } from '@/modules/session/types';
import { useUsersApi } from '@/composables/api/session/users';
import { useInterop } from '@/composables/electron-interop';
import { logger } from '@/modules/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useSessionAuthStore } from '@/store/session/auth';

interface UseChangePasswordReturn {
  changePassword: (payload: ChangePasswordPayload) => Promise<ActionStatus>;
}

export function useChangePassword(): UseChangePasswordReturn {
  const { username } = storeToRefs(useSessionAuthStore());
  const { showErrorMessage, showSuccessMessage } = useNotifications();
  const { changeUserPassword, colibriLogin, colibriLogout } = useUsersApi();
  const { clearPassword, isPackaged } = useInterop();
  const { t } = useI18n({ useScope: 'global' });

  const changePassword = async ({ currentPassword, newPassword }: ChangePasswordPayload): Promise<ActionStatus> => {
    try {
      const success = await changeUserPassword(get(username), currentPassword, newPassword);
      showSuccessMessage(t('actions.session.password_change.success'));

      if (success) {
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
      }

      return {
        success,
      };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      showErrorMessage(t('actions.session.password_change.error', { message }));
      return {
        message,
        success: false,
      };
    }
  };

  return {
    changePassword,
  };
}
