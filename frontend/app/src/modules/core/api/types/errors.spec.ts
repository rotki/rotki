import { describe, expect, it } from 'vitest';
import { ApiValidationError } from '@/modules/core/api/types/errors';

describe('apiValidationError', () => {
  function error(errors: Record<string, string[] | string>): ApiValidationError {
    return new ApiValidationError(JSON.stringify(errors));
  }

  it('should read the api field names as the frontend spells them', () => {
    expect(error({ from_timestamp: ['too late'] }).errors).toEqual({ fromTimestamp: ['too late'] });
  });

  it('should return the map when every field it names was sent', () => {
    const result = error({ address: ['unknown address'] })
      .getValidationErrors({ address: '', chain: 'all' });

    expect(result).toEqual({ address: ['unknown address'] });
  });

  it('should fall back to a single message when a field was not sent', () => {
    const result = error({ location: ['unknown exchange'] })
      .getValidationErrors({ address: '', chain: 'all' });

    expect(result).toBe('unknown exchange');
  });

  it('should fall back for a message the api sent unwrapped', () => {
    const result = error({ location: 'unknown exchange' })
      .getValidationErrors({ address: '' });

    expect(result).toBe('unknown exchange');
  });

  it('should fall back even when another field would have had somewhere to go', () => {
    const result = error({ from_timestamp: ['too late'], location: ['unknown exchange'] })
      .getValidationErrors({ fromTimestamp: 1 });

    expect(result).toBe('unknown exchange');
  });

  it('should keep the map when the caller has no payload to check against', () => {
    const result = error({ location: ['unknown exchange'] }).getValidationErrors({});

    expect(result).toEqual({ location: ['unknown exchange'] });
  });

  it('should fall back to the raw message when the body is not field errors', () => {
    const plain = new ApiValidationError('the backend is on fire');

    expect(plain.errors).toEqual({});
    expect(plain.getValidationErrors({ address: '' })).toBe('the backend is on fire');
  });
});
