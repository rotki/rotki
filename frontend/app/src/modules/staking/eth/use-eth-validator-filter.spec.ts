import { assert, describe, expect, it } from 'vitest';
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

  it('should coerce single route values into arrays', () => {
    const { RouteFilterSchema } = useEthValidatorAccountFilter();
    assert(RouteFilterSchema);

    expect(RouteFilterSchema.parse({ index: '5', publicKey: '0xabc', status: 'active' }))
      .toEqual({ index: ['5'], publicKey: ['0xabc'], status: ['active'] });
  });

  it('should keep array route values as arrays', () => {
    const { RouteFilterSchema } = useEthValidatorAccountFilter();
    assert(RouteFilterSchema);

    expect(RouteFilterSchema.parse({ status: ['active', 'exited'] }))
      .toEqual({ status: ['active', 'exited'] });
  });

  it('should allow an empty route filter', () => {
    const { RouteFilterSchema } = useEthValidatorAccountFilter();
    assert(RouteFilterSchema);

    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});
