import { describe, expect, it } from 'vitest';
import {
  INDETERMINATE,
  isTerminalStatus,
  percentageFromSteps,
  rollupPercentage,
  rollupStatus,
  statusRank,
} from './status';
import { ActivityStatus } from './types';

describe('task-center status helpers', () => {
  it('should rank live statuses ahead of terminal ones for dedup', () => {
    expect(statusRank(ActivityStatus.RUNNING)).toBeLessThan(statusRank(ActivityStatus.PENDING));
    expect(statusRank(ActivityStatus.PENDING)).toBeLessThan(statusRank(ActivityStatus.COMPLETE));
    expect(statusRank(ActivityStatus.FAILED)).toBeLessThan(statusRank(ActivityStatus.COMPLETE));
  });

  it('should treat complete/cancelled/failed/skipped as terminal and running/pending as not', () => {
    expect(isTerminalStatus(ActivityStatus.COMPLETE)).toBe(true);
    expect(isTerminalStatus(ActivityStatus.CANCELLED)).toBe(true);
    expect(isTerminalStatus(ActivityStatus.FAILED)).toBe(true);
    expect(isTerminalStatus(ActivityStatus.SKIPPED)).toBe(true);
    expect(isTerminalStatus(ActivityStatus.RUNNING)).toBe(false);
    expect(isTerminalStatus(ActivityStatus.PENDING)).toBe(false);
  });

  it('should prefer a run over a skip when deduplicating a shared id', () => {
    expect(statusRank(ActivityStatus.COMPLETE)).toBeLessThan(statusRank(ActivityStatus.SKIPPED));
    expect(statusRank(ActivityStatus.RUNNING)).toBeLessThan(statusRank(ActivityStatus.SKIPPED));
  });

  it('should compute a rounded step percentage and indeterminate when total is zero', () => {
    expect(percentageFromSteps(1, 4)).toBe(25);
    expect(percentageFromSteps(1, 3)).toBe(33);
    expect(percentageFromSteps(0, 0)).toBe(INDETERMINATE);
  });

  it('should roll up percentages ignoring indeterminate members', () => {
    expect(rollupPercentage([50, 100])).toBe(75);
    expect(rollupPercentage([INDETERMINATE, 80])).toBe(80);
    expect(rollupPercentage([INDETERMINATE, INDETERMINATE])).toBe(INDETERMINATE);
    expect(rollupPercentage([])).toBe(INDETERMINATE);
  });

  it('should roll up statuses by liveness priority', () => {
    expect(rollupStatus([ActivityStatus.COMPLETE, ActivityStatus.RUNNING])).toBe(ActivityStatus.RUNNING);
    expect(rollupStatus([ActivityStatus.COMPLETE, ActivityStatus.PENDING])).toBe(ActivityStatus.PENDING);
    expect(rollupStatus([ActivityStatus.COMPLETE, ActivityStatus.FAILED])).toBe(ActivityStatus.FAILED);
    expect(rollupStatus([ActivityStatus.CANCELLED, ActivityStatus.CANCELLED])).toBe(ActivityStatus.CANCELLED);
    expect(rollupStatus([ActivityStatus.COMPLETE, ActivityStatus.CANCELLED])).toBe(ActivityStatus.COMPLETE);
    expect(rollupStatus([])).toBe(ActivityStatus.COMPLETE);
  });

  it('should roll up to skipped only when every member was skipped, a partial skip not spoiling the run', () => {
    expect(rollupStatus([ActivityStatus.SKIPPED, ActivityStatus.SKIPPED])).toBe(ActivityStatus.SKIPPED);
    expect(rollupStatus([ActivityStatus.COMPLETE, ActivityStatus.SKIPPED])).toBe(ActivityStatus.COMPLETE);
    expect(rollupStatus([ActivityStatus.SKIPPED, ActivityStatus.FAILED])).toBe(ActivityStatus.FAILED);
    expect(rollupStatus([ActivityStatus.SKIPPED, ActivityStatus.RUNNING])).toBe(ActivityStatus.RUNNING);
  });
});
