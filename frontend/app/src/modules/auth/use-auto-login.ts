import type { Ref } from 'vue';
import { lastLogin } from '@/modules/auth/account-management';
import { useLogin } from '@/modules/auth/use-login';
import { usePasswordConfirmation } from '@/modules/auth/use-password-confirmation';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';

interface UseAutoLoginReturn {
  autolog: Ref<boolean>;
  needsPasswordConfirmation: Ref<boolean>;
  confirmPassword: (password: string) => Promise<boolean>;
  checkIfPasswordConfirmationNeeded: (usernameToCheck: string) => Promise<void>;
  username: Ref<string>;
}

export function useAutoLogin(): UseAutoLoginReturn {
  const autolog = shallowRef<boolean>(false);
  const isAutoLoginFlow = shallowRef<boolean>(false);

  const { login } = useLogin();
  const { connected } = storeToRefs(useMainStore());
  const authStore = useSessionAuthStore();
  const { canRequestData, logged, username } = storeToRefs(authStore);
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton } = usePremiumHelper();
  const { checkIfPasswordConfirmationNeeded, confirmPassword, needsPasswordConfirmation } = usePasswordConfirmation();

  watch(connected, async (connected) => {
    if (!connected)
      return;

    await resetSessionBackend();

    const savedUsername = get(lastLogin);
    if (!savedUsername) {
      // No saved credentials, can't auto-login
      return;
    }

    // Mark that we're starting an auto-login flow
    set(isAutoLoginFlow, true);
    set(autolog, true);

    // Try to login with empty password (auto-login)
    await login({ password: '', username: '' });

    set(autolog, false);
  });

  // Watch for successful auto-login and check if password confirmation is needed
  watch(logged, async (isLogged) => {
    // Only proceed if this is an auto-login flow
    if (!get(isAutoLoginFlow))
      return;

    if (!isLogged)
      return;

    // Reset the auto-login flow flag
    set(isAutoLoginFlow, false);

    const savedUsername = get(lastLogin);
    if (!savedUsername)
      return;

    // Check if password confirmation is needed AFTER successful auto-login
    await checkIfPasswordConfirmationNeeded(savedUsername);

    showGetPremiumButton();
    set(canRequestData, true);
  });

  return {
    autolog,
    checkIfPasswordConfirmationNeeded,
    confirmPassword,
    needsPasswordConfirmation,
    username,
  };
}
