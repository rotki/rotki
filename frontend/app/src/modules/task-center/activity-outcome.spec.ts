import { describe, expect, it } from 'vitest';
import { activityOutcome } from './activity-outcome';
import { ActivityStatus } from './core/types';

describe('activityOutcome', () => {
  /**
   * A running row without a percentage used to fall back to a spinner. The elapsed counter beside
   * it already ticks, so the spin carried no information the row was not already showing.
   */
  it('should give a running activity a label of its own', () => {
    expect(activityOutcome(ActivityStatus.RUNNING).color).toBe('primary');
  });

  /**
   * Filled means it needs attention. A refresh settles dozens of children successfully, so filling
   * those made a wall of green the loudest thing in the panel and buried the chain still at 0%.
   */
  it('should fill only the outcomes that need attention', () => {
    const filled = Object.values(ActivityStatus).filter(status => activityOutcome(status).variant === 'filled');

    expect(filled).toStrictEqual([ActivityStatus.FAILED]);
  });

  it('should give every status an icon', () => {
    for (const status of Object.values(ActivityStatus))
      expect(activityOutcome(status).icon).toBeDefined();
  });

  /**
   * Failed and skipped both count as *done* in the progress rollup (`projection.ts`), which is
   * correct — no further progress is coming — and is exactly why the row has to say what happened.
   * A subtree at 100% with two failed chains is otherwise indistinguishable from a clean one.
   */
  it('should separate a failure from a skip', () => {
    expect(activityOutcome(ActivityStatus.FAILED).color).toBe('error');
    expect(activityOutcome(ActivityStatus.SKIPPED).color).toBe('warning');
  });

  it('should mark a success and leave the neutral outcomes grey', () => {
    expect(activityOutcome(ActivityStatus.COMPLETE).color).toBe('success');
    expect(activityOutcome(ActivityStatus.CANCELLED).color).toBe('grey');
    expect(activityOutcome(ActivityStatus.PENDING).color).toBe('grey');
  });

  it('should give every status a label', () => {
    for (const status of Object.values(ActivityStatus))
      expect(activityOutcome(status).key).toBeDefined();
  });
});
