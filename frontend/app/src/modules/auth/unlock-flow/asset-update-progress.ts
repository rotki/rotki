import { StageStepStatus } from '@/modules/auth/stage/stage-step';
import { UnlockErrorKind, UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';

/** The three things that happen once the user accepts an asset update during login, in order. */
export const AssetUpdateStep = {
  APPLY: 'apply',
  RESTART: 'restart',
  SIGN_IN: 'sign-in',
} as const;

export type AssetUpdateStep = (typeof AssetUpdateStep)[keyof typeof AssetUpdateStep];

const ORDER: readonly AssetUpdateStep[] = [AssetUpdateStep.APPLY, AssetUpdateStep.RESTART, AssetUpdateStep.SIGN_IN];

export interface AssetUpdateStepRow {
  readonly step: AssetUpdateStep;
  readonly status: StageStepStatus;
}

/**
 * The step a phase of the unlock flow belongs to, once an update was accepted.
 *
 * @remarks
 * The restart phase also covers the re-authentication and reconnect that follow it, so the sign-in
 * step starts only when the flow unlocks the profile. `ready` is past every step.
 */
function stepOf(phase: string): AssetUpdateStep | undefined {
  switch (phase) {
    case UnlockPhase.applyingUpdate:
    case UnlockPhase.conflicts:
      return AssetUpdateStep.APPLY;
    case UnlockPhase.restarting:
      return AssetUpdateStep.RESTART;
    case UnlockPhase.authenticating:
    case UnlockPhase.connecting:
    case UnlockPhase.unlocking:
    case UnlockPhase.loadingSession:
      return AssetUpdateStep.SIGN_IN;
    default:
      return undefined;
  }
}

/** The step a failure stopped at, read from the kind of error the flow parked with. */
function failedStepOf(errorKind: string): AssetUpdateStep {
  if (errorKind === UnlockErrorKind.updateFailed)
    return AssetUpdateStep.APPLY;
  if (errorKind === UnlockErrorKind.restartFailed)
    return AssetUpdateStep.RESTART;
  return AssetUpdateStep.SIGN_IN;
}

/**
 * Lays out the post-update checklist for the phase the unlock flow is in.
 *
 * @param phase - the unlock flow's current phase
 * @param errorKind - the error the flow stopped with, when the phase is `error`
 * @returns every step, each marked done, current, failed or pending
 */
export function assetUpdateSteps(phase: string, errorKind?: string): AssetUpdateStepRow[] {
  const failed = phase === UnlockPhase.error && errorKind !== undefined;
  const at = failed ? failedStepOf(errorKind) : stepOf(phase);
  let index = at === undefined ? 0 : ORDER.indexOf(at);
  if (phase === UnlockPhase.ready)
    index = ORDER.length;

  return ORDER.map((step, position) => {
    if (position < index)
      return { status: StageStepStatus.DONE, step };
    if (position === index)
      return { status: failed ? StageStepStatus.FAILED : StageStepStatus.CURRENT, step };
    return { status: StageStepStatus.PENDING, step };
  });
}
