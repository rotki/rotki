import { describe, expect, it } from 'vitest';
import { isValidStatus, validStatuses } from '@/modules/staking/eth/use-eth-validator-filter';

describe('isValidStatus', () => {
  it('should accept known statuses', () => {
    for (const status of validStatuses) {
      expect(isValidStatus(status)).toBe(true);
    }
  });

  it('should reject unknown statuses', () => {
    expect(isValidStatus('unknown')).toBe(false);
    expect(isValidStatus('')).toBe(false);
  });
});
