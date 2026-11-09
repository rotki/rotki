import { describe, expect, it } from 'vitest';
import { FailureCause, isRetryableCause, parseFailureCause } from '@/modules/core/api/failure-cause';

describe('parseFailureCause', () => {
  it('should keep every value the backend sends', () => {
    expect(parseFailureCause('remote_rejected')).toBe(FailureCause.REMOTE_REJECTED);
  });

  it.each([undefined, null, 'from_the_future', 502])('should read %s as unknown', (value) => {
    expect(parseFailureCause(value)).toBe(FailureCause.UNKNOWN);
  });
});

describe('isRetryableCause', () => {
  it.each([
    FailureCause.BAD_DATA,
    FailureCause.NETWORK,
    FailureCause.RATE_LIMITED,
    FailureCause.UNKNOWN,
  ])('should offer a retry for %s', (cause) => {
    expect(isRetryableCause(cause)).toBe(true);
  });

  it.each([
    FailureCause.AUTH,
    FailureCause.CANCELLED,
    FailureCause.CONFLICT,
    FailureCause.FORBIDDEN,
    FailureCause.INTERNAL,
    FailureCause.INVALID_INPUT,
    FailureCause.LOCAL_DB,
    FailureCause.NOT_FOUND,
    FailureCause.REMOTE_REJECTED,
    FailureCause.UNSUPPORTED,
  ])('should offer no retry for %s', (cause) => {
    expect(isRetryableCause(cause)).toBe(false);
  });
});
