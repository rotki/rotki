import type { Ref } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

/** How a restore of the server backup ended, which decides how the login screen words it. */
export const RestoreOutcomeKind = {
  RESTORED: 'restored',
  FAILED: 'failed',
} as const;

export type RestoreOutcomeKind = (typeof RestoreOutcomeKind)[keyof typeof RestoreOutcomeKind];

export interface RestoreOutcome {
  readonly kind: RestoreOutcomeKind;
  readonly message: string;
}

interface UseRestoreOutcomeNoticeReturn {
  /** How the last restore ended, while the login screen should say so. */
  outcome: Readonly<Ref<RestoreOutcome | undefined>>;
  show: (outcome: RestoreOutcome) => void;
  dismiss: () => void;
}

/**
 * Why the user is back at the login screen after restoring the server backup.
 *
 * @remarks
 * A restore always ends in a logout, which takes the dock row that reported it along. Global
 * rather than a store, so the logout's store reset leaves it for the login screen to show. It
 * goes away once the user is logged in again. Not when a session begins: an auto-login that
 * starts on the login screen and fails begins one too, and would hide it before it was read.
 */
export const useRestoreOutcomeNotice = createGlobalState((): UseRestoreOutcomeNoticeReturn => {
  const outcome = shallowRef<RestoreOutcome>();
  const { logged } = storeToRefs(useSessionAuthStore());

  const show = (restoreOutcome: RestoreOutcome): void => {
    set(outcome, restoreOutcome);
  };

  const dismiss = (): void => {
    set(outcome, undefined);
  };

  watch(logged, (isLogged) => {
    if (isLogged)
      dismiss();
  });

  return {
    dismiss,
    outcome: readonly(outcome),
    show,
  };
});
