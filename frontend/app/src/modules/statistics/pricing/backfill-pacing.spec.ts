import { describe, expect, it } from 'vitest';
import {
  BACKOFF_MAX_MS,
  BACKOFF_START_MS,
  nextPacing,
  REQUEST_DELAY_MS,
} from '@/modules/statistics/pricing/backfill-pacing';

describe('modules/statistics/pricing/backfill-pacing', () => {
  it('should wait the normal pace after a request goes through', () => {
    expect(nextPacing(false, 0)).toEqual({ backoff: 0, delay: REQUEST_DELAY_MS });
  });

  it('should double the wait on each rate limit, up to the cap', () => {
    expect(nextPacing(true, 0).delay).toBe(BACKOFF_START_MS);
    expect(nextPacing(true, BACKOFF_START_MS).delay).toBe(2 * BACKOFF_START_MS);
    expect(nextPacing(true, BACKOFF_MAX_MS).delay).toBe(BACKOFF_MAX_MS);
  });

  it('should reset the backoff once a request goes through', () => {
    expect(nextPacing(false, BACKOFF_MAX_MS).backoff).toBe(0);
  });
});
