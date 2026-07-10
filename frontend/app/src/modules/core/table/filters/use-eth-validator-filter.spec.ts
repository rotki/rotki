import { assert, describe, expect, it } from 'vitest';
import {
  isValidStatus,
  useEthValidatorAccountFilter,
  validStatuses,
} from '@/modules/core/table/filters/use-eth-validator-filter';

const t = (key: string): string => key;

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
    const { filters } = useEthValidatorAccountFilter(t);
    expect(get(filters)).toEqual({});
  });

  it('should expose matchers for index, public key and status', () => {
    const { matchers } = useEthValidatorAccountFilter(t);
    const keys = get(matchers).map(matcher => matcher.key);
    expect(keys).toEqual(['validator_index', 'public_key', 'status']);
  });

  it('should suggest all statuses except all', () => {
    const { matchers } = useEthValidatorAccountFilter(t);
    const statusMatcher = get(matchers).find(matcher => matcher.key === 'status');
    assert(statusMatcher && 'string' in statusMatcher);
    expect(statusMatcher.suggestions()).toEqual(['exited', 'active', 'consolidated']);
  });

  it('should validate the status value against the known statuses', () => {
    const { matchers } = useEthValidatorAccountFilter(t);
    const statusMatcher = get(matchers).find(matcher => matcher.key === 'status');
    assert(statusMatcher && 'string' in statusMatcher);
    expect(statusMatcher.validate('active')).toBe(true);
    expect(statusMatcher.validate('nope')).toBe(false);
  });

  it('should coerce single route values into arrays', () => {
    const { RouteFilterSchema } = useEthValidatorAccountFilter(t);
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ index: '5', publicKey: '0xabc', status: 'active' }))
      .toEqual({ index: ['5'], publicKey: ['0xabc'], status: ['active'] });
  });

  it('should keep array route values as arrays', () => {
    const { RouteFilterSchema } = useEthValidatorAccountFilter(t);
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ status: ['active', 'exited'] }))
      .toEqual({ status: ['active', 'exited'] });
  });

  it('should allow an empty route filter', () => {
    const { RouteFilterSchema } = useEthValidatorAccountFilter(t);
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});
