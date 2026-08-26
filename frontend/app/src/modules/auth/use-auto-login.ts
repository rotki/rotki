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

  // `immediate` so it also fires when this is created after the backend already connected
  // (e.g. the login screen mounts post-connect) rather than only on a false→true transition.
  watch(connected, async (isConnected) => {
    if (!isConnected)
      return;

    set(autolog, true);

    await resetSessionBackend();

    // No saved profile ⇒ nothing to auto-unlock; drop the loader and show the login form.
    if (!get(lastLogin)) {
      set(autolog, false);
      return;
    }

    await controller.startAuto();

    if (get(controller.state).kind !== UnlockPhase.ready)
      set(autolog, false);
  }, { immediate: true });

  return {
    autolog: readonly(autolog),
    checkIfPasswordConfirmationNeeded,
    confirmPassword,
    needsPasswordConfirmation,
    username,
  };
}

export const useAutoLogin = createSharedComposable(createAutoLogin);
