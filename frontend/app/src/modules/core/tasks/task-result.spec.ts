import { err, ok } from 'plainfp/result';
import { assert, describe, expect, it, vi } from 'vitest';
import {
  BackendCancelled,
  Cancelled,
  errorOf,
  isActionable,
  isCancellation,
  onActionableError,
  TaskFailed,
} from './task-result';

describe('isCancellation', () => {
  it('should be true for a user cancellation', () => {
    expect(isCancellation(Cancelled({ message: 'boom' }))).toBe(true);
  });

  it('should be true for a backend cancellation', () => {
    expect(isCancellation(BackendCancelled({ message: 'boom' }))).toBe(true);
  });

  it('should be false for an actionable failure', () => {
    expect(isCancellation(TaskFailed({ message: 'boom' }))).toBe(false);
  });
});

describe('isActionable', () => {
  it('should narrow a TaskFailed to the arm carrying the cause', () => {
    const cause = new Error('network');
    const error = TaskFailed({ cause, message: 'boom' });

    assert(isActionable(error));
    expect(error.cause).toBe(cause);
  });

  it('should be false for either cancellation', () => {
    expect(isActionable(Cancelled({ message: 'boom' }))).toBe(false);
    expect(isActionable(BackendCancelled({ message: 'boom' }))).toBe(false);
  });
});

describe('errorOf', () => {
  it('should return the original cause so a subclass survives', () => {
    class ApiError extends Error {
      override name = 'ApiError';
    }
    const cause = new ApiError('{"address": ["invalid"]}');

    const error = errorOf(TaskFailed({ cause, message: 'wrapped' }));

    expect(error).toBe(cause);
    expect(error).toBeInstanceOf(ApiError);
  });

  it('should wrap the message when the cause is not an Error', () => {
    expect(errorOf(TaskFailed({ cause: 'a string', message: 'wrapped' }))).toStrictEqual(new Error('wrapped'));
    expect(errorOf(TaskFailed({ message: 'wrapped' }))).toStrictEqual(new Error('wrapped'));
  });

  it('should wrap the message for a cancellation, which carries no cause', () => {
    expect(errorOf(Cancelled({ message: 'cancelled' }))).toStrictEqual(new Error('cancelled'));
  });
});

describe('onActionableError', () => {
  it('should run the handler on an actionable failure', () => {
    const handler = vi.fn();
    const error = TaskFailed({ message: 'boom' });

    onActionableError(err(error), handler);

    expect(handler).toHaveBeenCalledWith(error);
  });

  it('should stay silent on a cancellation', () => {
    const handler = vi.fn();

    onActionableError(err(Cancelled({ message: 'boom' })), handler);

    expect(handler).not.toHaveBeenCalled();
  });

  it('should stay silent on success', () => {
    const handler = vi.fn();

    onActionableError(ok(42), handler);

    expect(handler).not.toHaveBeenCalled();
  });
});
