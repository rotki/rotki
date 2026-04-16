import type { Ref } from 'vue';
import dayjs from 'dayjs';
import { useRememberSettings } from '@/modules/auth/use-remember-settings';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UsePasswordConfirmationReturn {
  checkIfPasswordConfirmationNeeded: (usernameToCheck: string) => Promise<void>;
  confirmPassword: (password: string) => Promise<boolean>;
  needsPasswordConfirmation: Ref<boolean>;
}

export function usePasswordConfirmation(): UsePasswordConfirmationReturn {
  const { getPassword, isPackaged } = useInterop();
  const authStore = useSessionAuthStore();
  const { needsPasswordConfirmation, username } = storeToRefs(authStore);
  const frontendSettingsStore = useFrontendSettingsStore();
  const { updateFrontendSetting } = useSettingsOperations();
  const { enablePasswordConfirmation, lastPasswordConfirmed, passwordConfirmationInterval } = storeToRefs(frontendSettingsStore);
  const { savedRememberPassword } = useRememberSettings();

  const checkIfPasswordConfirmationNeeded = async (usernameToCheck: string): Promise<void> => {
    if (!get(enablePasswordConfirmation) || !isPackaged)
      return;

    if (!get(savedRememberPassword))
      return;

    const lastConfirmed = get(lastPasswordConfirmed);
    const now = dayjs().unix();

    if (lastConfirmed === 0) {
      await updateFrontendSetting({ lastPasswordConfirmed: now });
      return;
    }

    if ((now - lastConfirmed) <= get(passwordConfirmationInterval))
      return;

    const storedPassword = await getPassword(usernameToCheck);
    if (!storedPassword)
      return;

    set(needsPasswordConfirmation, true);
  };

  const confirmPassword = async (password: string): Promise<boolean> => {
    const storedPassword = await getPassword(get(username));

    if (password === storedPassword) {
      set(needsPasswordConfirmation, false);
      const now = dayjs().unix();
      await updateFrontendSetting({ lastPasswordConfirmed: now });
      return true;
    }

    return false;
  };

  return {
    checkIfPasswordConfirmationNeeded,
    confirmPassword,
    needsPasswordConfirmation,
  };
}
