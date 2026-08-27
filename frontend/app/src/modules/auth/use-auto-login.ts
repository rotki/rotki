import type { Ref } from 'vue';
import { lastLogin } from '@/modules/auth/account-management';
import { UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';
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
 * Auto-unlock on backend (re)connection — the single trigger for it. When a saved profile
 * exists it kicks off `controller.startAuto()`, which resolves the stored credentials and
 * drives the ONE shared flow: the flow probes for a live session and either resumes it or
 * does a fresh login with the saved password. Post-unlock side-effects run in the
 * controller's `ready` handler, so this only starts the flow.
 *
 * Exposed as a shared singleton (see `useAutoLogin` below): `autolog` and the `connected`
 * watch MUST be shared so every consumer (UserHost, AppMessages) reads the same loading flag
 * and there is exactly one watcher. With a per-instance copy the "loser" of the `canStart`
 * race flips its own `autolog` back to false while the winner's flow is still running, so the
 * login form flashes instead of the loader.
 */
export function createAutoLogin(): UseAutoLoginReturn {
  const autolog = shallowRef<boolean>(false);

  const controller = useUnlockFlowController();
  const { connected } = storeToRefs(useMainStore());
  const { username } = storeToRefs(useSessionAuthStore());
  const { resetSessionBackend } = useBackendManagement();
  const { checkIfPasswordConfirmationNeeded, confirmPassword, needsPasswordConfirmation } = usePasswordConfirmation();

  /**
   * Attempts to unlock the last profile as soon as the backend is reachable.
   *
   * @remarks
   * Watched immediately rather than on a false-to-true transition, so it still runs where the
   * backend connected before this was created, which is what the login screen mounting post-connect
   * does. With no saved profile there is nothing to unlock, so the loader is dropped and the login
   * form shown.
   *
   * @param isConnected - whether the backend is reachable
   */
  async function unlockLastProfile(isConnected: boolean): Promise<void> {
    if (!isConnected)
      return;

    set(autolog, true);

    await resetSessionBackend();

    if (!get(lastLogin)) {
      set(autolog, false);
      return;
    }

    await controller.startAuto();

    if (get(controller.state).kind !== UnlockPhase.ready)
      set(autolog, false);
  }

  watch(connected, unlockLastProfile, { immediate: true });

  return {
    autolog: readonly(autolog),
    checkIfPasswordConfirmationNeeded,
    confirmPassword,
    needsPasswordConfirmation,
    username,
  };
}

export const useAutoLogin = createSharedComposable(createAutoLogin);
