import { describe, expect, it } from 'vitest';
import {
  isValidStatus,
  useEthValidatorAccountFilter,
  validStatuses,
} from '@/modules/staking/eth/use-eth-validator-filter';

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

describe('useEthValidatorAccountFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useEthValidatorAccountFilter();

    expect(get(filters)).toEqual({});
  });

  // The URL round-trip is asserted in `use-eth-validator-fields.spec.ts`, against the field list
  // the url shape is now derived from.
});
