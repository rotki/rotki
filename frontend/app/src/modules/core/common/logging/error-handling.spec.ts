import { describe, expect, it } from 'vitest';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';

describe('getErrorMessage', () => {
  it('should return the message from an Error instance', () => {
    expect(getErrorMessage(new Error('something broke'))).toBe('something broke');
  });

  it('should return the message from a subclass of Error', () => {
    class ApiValidationError extends Error {
      constructor(message: string) {
        super(message);
        this.name = 'ApiValidationError';
      }
    }
    expect(getErrorMessage(new ApiValidationError('bad input'))).toBe('bad input');
  });

  it('should return a string error directly', () => {
    expect(getErrorMessage('raw string')).toBe('raw string');
  });

  it('should return the stringified message from an object with a message property', () => {
    expect(getErrorMessage({ message: 'object error' })).toBe('object error');
  });

  it('should stringify non-string message properties', () => {
    expect(getErrorMessage({ message: 42 })).toBe('42');
  });

  it('should return fallback for null', () => {
    expect(getErrorMessage(null)).toBe('Unknown error occurred');
  });

  it('should return fallback for undefined', () => {
    expect(getErrorMessage(undefined)).toBe('Unknown error occurred');
  });

  it('should return fallback for a number', () => {
    expect(getErrorMessage(123)).toBe('Unknown error occurred');
  });

  it('should return fallback for an empty object', () => {
    expect(getErrorMessage({})).toBe('Unknown error occurred');
  });
});
