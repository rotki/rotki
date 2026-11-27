import type { ConflictResolution } from '@/modules/assets/types';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type Ref } from 'vue';
import { UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import { useUnlockFlowController } from '@/modules/auth/unlock-flow/use-unlock-flow-controller';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

interface UseLoginStageReturn {
  /** The shared unlock flow's current phase, handed to the unlock stage. */
  state: Readonly<Ref<UnlockState>>;
  /** Whether the stage takes over from the login form. */
  showStage: ComputedRef<boolean>;
  /** Clears a previous session's terminal state from the shared flow. */
  reset: () => void;
  /** Applies the asset update up to the confirmed version. */
  onConfirmUpdate: (upToVersion: number) => void;
  /** Applies the asset update with the chosen conflict resolution. */
  onResolveConflicts: (resolution: ConflictResolution) => void;
  /** Skips the asset update. */
  onSkipUpdate: () => void;
  /** Leaves a failed upgrade's screen for the login form. */
  onLeaveFailedUpgrade: () => void;
}

/** The phases a DB upgrade is shown through: while it runs, and while the session it unlocked loads. */
const UPGRADE_PHASES: ReadonlySet<string> = new Set([
  UnlockPhase.unlocking,
  UnlockPhase.loadingSession,
  UnlockPhase.ready,
]);

/**
 * Drives the login page's unlock stage from the shared unlock flow controller: which phase shows
 * its own UI instead of the form, and the handlers for the stage's events.
 */
export function useLoginStage(): UseLoginStageReturn {
  const { applyUpdate, reset, skipUpdate, state, upgradeVisible } = useUnlockFlowController();
  const authStore = useSessionAuthStore();
  const { upgradeFailure } = storeToRefs(authStore);

  /**
   * Whether the stage takes over from the login form.
   *
   * @remarks
   * Only for the phases needing their own UI, being an asset update and a DB upgrade during unlock.
   * The form stays mounted through the transient authenticate, connect and unlock phases, showing its
   * own loading state, so that a wrong-password error and the typed password both survive rather than
   * the form remounting empty on the way back.
   *
   * A DB upgrade keeps the stage until the app opens, so its finished state is the handoff, and keeps
   * it after a failure, so the failure is explained where the progress was.
   */
  const showStage = computed<boolean>(() => {
    const kind = get(state).kind;
    return kind === UnlockPhase.updatePrompt
      || kind === UnlockPhase.conflicts
      || kind === UnlockPhase.applyingUpdate
      || kind === UnlockPhase.restarting
      || (UPGRADE_PHASES.has(kind) && get(upgradeVisible))
      || (kind === UnlockPhase.error && get(upgradeFailure) !== null);
  });

  function onConfirmUpdate(upToVersion: number): void {
    startPromise(applyUpdate(undefined, upToVersion));
  }

  function onResolveConflicts(resolution: ConflictResolution): void {
    startPromise(applyUpdate(resolution));
  }

  function onSkipUpdate(): void {
    startPromise(skipUpdate());
  }

  /** Returns the flow to the idle form, dropping a failed upgrade's screen with it. */
  function resetStage(): void {
    authStore.clearUpgradeMessages();
    reset();
  }

  return {
    onConfirmUpdate,
    onLeaveFailedUpgrade: resetStage,
    onResolveConflicts,
    onSkipUpdate,
    reset: resetStage,
    showStage,
    state,
  };
}
