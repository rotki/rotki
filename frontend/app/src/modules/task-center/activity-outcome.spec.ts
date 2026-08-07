import { describe, expect, it } from 'vitest';
import { activityOutcome } from './activity-outcome';
import { ActivityStatus } from './core/types';

describe('activityOutcome', () => {
  it('should leave a running activity to its progress indicator', () => {
    expect(activityOutcome(ActivityStatus.RUNNING)).toBeUndefined();
  });

  /**
   * Failed and skipped both count as *done* in the progress rollup (`projection.ts`), which is
   * correct — no further progress is coming — and is exactly why the row has to say what happened.
   * A subtree at 100% with two failed chains is otherwise indistinguishable from a clean one.
   */
  it('should separate a failure from a skip', () => {
    expect(activityOutcome(ActivityStatus.FAILED)?.color).toBe('error');
    expect(activityOutcome(ActivityStatus.SKIPPED)?.color).toBe('warning');
  });

  it('should mark a success and leave the neutral outcomes grey', () => {
    expect(activityOutcome(ActivityStatus.COMPLETE)?.color).toBe('success');
    expect(activityOutcome(ActivityStatus.CANCELLED)?.color).toBe('grey');
    expect(activityOutcome(ActivityStatus.PENDING)?.color).toBe('grey');
  });

  it('should give every non-running status a label', () => {
    const statuses = Object.values(ActivityStatus).filter(status => status !== ActivityStatus.RUNNING);

    for (const status of statuses)
      expect(activityOutcome(status)?.key).toBeDefined();
  });
});
