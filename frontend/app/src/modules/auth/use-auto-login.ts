import type { Ref } from 'vue';
import { lastLogin } from '@/modules/auth/account-management';
import { useUnlockFlowController } from '@/modules/auth/unlock-flow/use-unlock-flow-controller';
import { usePasswordConfirmation } from '@/modules/auth/use-password-confirmation';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';

interface UseAutoLoginReturn {
  autolog: Readonly<Ref<boolean>>;
  needsPasswordConfirmation: Ref<boolean>;
  confirmPassword: (password: string) => Promise<boolean>;
  checkIfPasswordConfirmationNeeded: (usernameToCheck: string) => Promise<void>;
  username: Ref<string>;
}

/**
 * Auto-login on backend (re)connection: when a saved profile exists, resume the session
 * through the shared unlock-flow controller. Resume uses the `resume` step-set (no
 * asset-update prompt) and the post-unlock side-effects — including the password-confirmation
 * check — run in the controller's `ready` handler, so this only kicks the flow off.
 */
export function useAutoLogin(): UseAutoLoginReturn {
  const autolog = shallowRef<boolean>(false);

  const controller = useUnlockFlowController();
  const { connected } = storeToRefs(useMainStore());
  const { username } = storeToRefs(useSessionAuthStore());
  const { resetSessionBackend } = useBackendManagement();
  const { checkIfPasswordConfirmationNeeded, confirmPassword, needsPasswordConfirmation } = usePasswordConfirmation();

  watch(connected, async (isConnected) => {
    if (!isConnected)
      return;

    await resetSessionBackend();

    // No saved credentials ⇒ nothing to resume; show the login form.
    if (!get(lastLogin))
      return;

    set(autolog, true);
    await controller.startResume();
    set(autolog, false);
  });

  return {
    autolog: readonly(autolog),
    checkIfPasswordConfirmationNeeded,
    confirmPassword,
    needsPasswordConfirmation,
    username,
  };
}
