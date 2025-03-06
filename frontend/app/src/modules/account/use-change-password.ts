import { logger } from '@/utils/logging';
import { useMessageStore } from '@/store/message';
import { useUsersApi } from '@/composables/api/session/users';
import { useInterop } from '@/composables/electron-interop';
import { useSessionAuthStore } from '@/store/session/auth';
import type { ChangePasswordPayload } from '@/types/session';
import type { ActionStatus } from '@/types/action';

interface UseChangePasswordReturn {
  changePassword: (payload: ChangePasswordPayload) => Promise<ActionStatus>;
}

export function useChangePassword(): UseChangePasswordReturn {
  const { username } = storeToRefs(useSessionAuthStore());
  const { setMessage } = useMessageStore();
  const { changeUserPassword } = useUsersApi();
  const { clearPassword, isPackaged } = useInterop();
  const { t } = useI18n({ useScope: 'global' });

  const changePassword = async ({ currentPassword, newPassword }: ChangePasswordPayload): Promise<ActionStatus> => {
    try {
      const success = await changeUserPassword(get(username), currentPassword, newPassword);
      setMessage({
        description: t('actions.session.password_change.success'),
        success: true,
      });

      if (success && isPackaged) {
        clearPassword()
          .then(() => logger.info('clear complete'))
          .catch(error => logger.error(error));
      }

      return {
        success,
      };
    }
    catch (error: any) {
      setMessage({
        description: t('actions.session.password_change.error', {
          message: error.message,
        }),
      });
      return {
        message: error.message,
        success: false,
      };
    }
  };

  return {
    changePassword,
  };
}
