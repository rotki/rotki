import { describe, expect, it } from 'vitest';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { useSaveFailure } from '@/modules/core/form/use-save-failure';

describe('useSaveFailure', () => {
  const payload = { name: 'Party', description: '' };

  it('should file validation errors under the fields they name, with no failure', () => {
    const { capture, failure, modelFieldErrors } = useSaveFailure();

    capture(new ApiValidationError(JSON.stringify({ name: 'already taken' })), payload);

    expect(get(modelFieldErrors)).toEqual({ name: ['already taken'] });
    expect(get(failure)).toBeUndefined();
  });

  it('should make a validation error on a key outside the payload the failure', () => {
    const { capture, failure, modelFieldErrors } = useSaveFailure();

    capture(new ApiValidationError(JSON.stringify({ _schema: ['rejected as a whole'] })), payload);

    expect(get(failure)).toBe('rejected as a whole');
    expect(get(modelFieldErrors)).toEqual({});
  });

  it('should keep any other error as thrown, so the strip can word it', () => {
    const { capture, failure } = useSaveFailure();
    const error = new Error('database locked');

    capture(error, payload);

    expect(get(failure)).toBe(error);
  });

  it('should drop the previous outcome on each capture and on clear', () => {
    const { capture, clear, failure, modelFieldErrors } = useSaveFailure();

    capture(new ApiValidationError(JSON.stringify({ name: 'already taken' })), payload);
    capture(new Error('database locked'), payload);
    expect(get(modelFieldErrors)).toEqual({});

    clear();
    expect(get(failure)).toBeUndefined();
  });
});
