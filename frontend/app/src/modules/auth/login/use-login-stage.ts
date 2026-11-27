import type { ConflictResolution } from '@/modules/assets/types';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, readonly, type Ref, shallowRef, watch } from 'vue';
import { showsUpgrade } from '@/modules/auth/unlock-flow/upgrade-stage';
import { UnlockErrorKind, UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import { useUnlockFlowController } from '@/modules/auth/unlock-flow/use-unlock-flow-controller';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

interface UseLoginStageReturn {
  /** The shared unlock flow's current phase, handed to the unlock stage. */
  state: Readonly<Ref<UnlockState>>;
  /** Whether the stage takes over from the login form. */
  showStage: ComputedRef<boolean>;
  /** Whether the user accepted an asset update in this unlock, so its progress stays on screen. */
  updateAccepted: Readonly<Ref<boolean>>;
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
 * The errors an accepted asset update explains on its own progress screen. A sync conflict or an
 * incomplete upgrade needs the form's prompt instead, and a wrong password the form's field.
 */
const UPDATE_ERRORS: ReadonlySet<string> = new Set([
  UnlockErrorKind.updateFailed,
  UnlockErrorKind.restartFailed,
  UnlockErrorKind.unknown,
]);

/**
 * Drives the login page's unlock stage from the shared unlock flow controller: which phase shows
 * its own UI instead of the form, and the handlers for the stage's events.
 */
export function useLoginStage(): UseLoginStageReturn {
  const { applyUpdate, reset, skipUpdate, state, upgradeVisible } = useUnlockFlowController();
  const { upgradeFailure } = storeToRefs(useSessionAuthStore());

  const updateAccepted = shallowRef<boolean>(false);

  watch(() => get(state).kind, (kind) => {
    if (kind === UnlockPhase.applyingUpdate)
      set(updateAccepted, true);
    else if (kind === UnlockPhase.idle || kind === UnlockPhase.updatePrompt)
      set(updateAccepted, false);
  }, { flush: 'sync' });

  /** Whether the phase is part of an accepted update's run, from applying it to opening the app. */
  function inUpdateRun(current: UnlockState): boolean {
    if (!get(updateAccepted))
      return false;
    if (current.kind === UnlockPhase.error)
      return UPDATE_ERRORS.has(current.error.kind);
    return current.kind !== UnlockPhase.idle;
  }

  /**
   * Whether the stage takes over from the login form.
   *
   * @remarks
   * For the phases needing their own UI: the asset update prompt and conflicts, an accepted update
   * all the way to the app opening, and a DB upgrade during unlock. Otherwise the form stays mounted
   * through the transient authenticate, connect and unlock phases, showing its own loading state, so
   * that a wrong-password error and the typed password both survive rather than the form remounting
   * empty on the way back.
   *
   * An accepted update keeps the stage through the restart and the sign-in after it, so the steps it
   * lists finish where they started instead of the form coming back for a moment, and keeps it after
   * a failure, which it explains.
   *
   * A DB upgrade keeps the stage until the app opens, so its finished state is the handoff, and keeps
   * it after a failure, so the failure is explained where the progress was.
   */
  const showStage = computed<boolean>(() => {
    const current = get(state);
    const kind = current.kind;
    return kind === UnlockPhase.updatePrompt
      || kind === UnlockPhase.conflicts
      || kind === UnlockPhase.applyingUpdate
      || inUpdateRun(current)
      || showsUpgrade(kind, get(upgradeVisible), get(upgradeFailure) !== null);
  });

  function onConfirmUpdate(upToVersion: number): void {
    startPromise(applyUpdate(undefined, upToVersion));
  }

  function onResolveConflicts(resolution: ConflictResolution): void {
    startPromise(applyUpdate(resolution));
  }

  function onSkipUpdate(): void {
    set(updateAccepted, false);
    startPromise(skipUpdate());
  }

  return {
    onConfirmUpdate,
    onResolveConflicts,
    onSkipUpdate,
    reset,
    showStage,
    state,
    updateAccepted: readonly(updateAccepted),
  };
}
