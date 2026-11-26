import type { ConflictResolution } from '@/modules/assets/types';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type Ref } from 'vue';
import { UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import { useUnlockFlowController } from '@/modules/auth/unlock-flow/use-unlock-flow-controller';

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
}

/**
 * Drives the login page's unlock stage from the shared unlock flow controller: which phase shows
 * its own UI instead of the form, and the handlers for the stage's events.
 */
export function useLoginStage(): UseLoginStageReturn {
  const { applyUpdate, reset, skipUpdate, state, upgradeVisible } = useUnlockFlowController();

  /**
   * Whether the stage takes over from the login form.
   *
   * @remarks
   * Only for the phases needing their own UI, being an asset update and a DB upgrade during unlock.
   * The form stays mounted through the transient authenticate, connect and unlock phases, showing its
   * own loading state, so that a wrong-password error and the typed password both survive rather than
   * the form remounting empty on the way back.
   */
  const showStage = computed<boolean>(() => {
    const kind = get(state).kind;
    return kind === UnlockPhase.updatePrompt
      || kind === UnlockPhase.conflicts
      || kind === UnlockPhase.applyingUpdate
      || kind === UnlockPhase.restarting
      || (kind === UnlockPhase.unlocking && get(upgradeVisible));
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

  return {
    onConfirmUpdate,
    onResolveConflicts,
    onSkipUpdate,
    reset,
    showStage,
    state,
  };
}
