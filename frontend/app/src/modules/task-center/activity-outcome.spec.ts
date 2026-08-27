import { describe, expect, it } from 'vitest';
import { activityOutcome } from './activity-outcome';
import { ActivityStatus } from './core/types';

describe('activityOutcome', () => {
  it('should give a running activity a label of its own, rather than a spinner', () => {
    expect(activityOutcome(ActivityStatus.RUNNING).color).toBe('primary');
  });

  it('should fill only the outcomes that need attention', () => {
    const filled = Object.values(ActivityStatus).filter(status => activityOutcome(status).variant === 'filled');

    expect(filled).toStrictEqual([ActivityStatus.FAILED]);
  });

  it('should give every status an icon', () => {
    for (const status of Object.values(ActivityStatus))
      expect(activityOutcome(status).icon).toBeDefined();
  });

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
