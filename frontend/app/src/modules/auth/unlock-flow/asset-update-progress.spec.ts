import { describe, expect, it } from 'vitest';
import { StageStepStatus } from '@/modules/auth/stage/stage-step';
import { assetUpdateSteps } from '@/modules/auth/unlock-flow/asset-update-progress';
import { UnlockErrorKind, UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';

function statuses(phase: string, errorKind?: string): StageStepStatus[] {
  return assetUpdateSteps(phase, errorKind).map(({ status }) => status);
}

const { CURRENT, DONE, FAILED, PENDING } = StageStepStatus;

describe('modules/auth/unlock-flow/asset-update-progress', () => {
  it('should list apply, restart and sign in, in that order', () => {
    expect(assetUpdateSteps(UnlockPhase.applyingUpdate).map(({ step }) => step)).toStrictEqual(['apply', 'restart', 'sign-in']);
  });

  it.each([
    [UnlockPhase.applyingUpdate, [CURRENT, PENDING, PENDING]],
    [UnlockPhase.conflicts, [CURRENT, PENDING, PENDING]],
    [UnlockPhase.restarting, [DONE, CURRENT, PENDING]],
    [UnlockPhase.authenticating, [DONE, DONE, CURRENT]],
    [UnlockPhase.unlocking, [DONE, DONE, CURRENT]],
    [UnlockPhase.loadingSession, [DONE, DONE, CURRENT]],
    [UnlockPhase.ready, [DONE, DONE, DONE]],
  ])('should mark the steps for %s', (phase, expected) => {
    expect(statuses(phase)).toStrictEqual(expected);
  });

  it.each([
    [UnlockErrorKind.updateFailed, [FAILED, PENDING, PENDING]],
    [UnlockErrorKind.restartFailed, [DONE, FAILED, PENDING]],
    [UnlockErrorKind.unknown, [DONE, DONE, FAILED]],
  ])('should mark the step a %s error stopped at as failed', (errorKind, expected) => {
    expect(statuses(UnlockPhase.error, errorKind)).toStrictEqual(expected);
  });
});
